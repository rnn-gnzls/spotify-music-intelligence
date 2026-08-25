import os
import base64
import secrets
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
    redirect,
    session
)
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env")

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio_files"

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv(
    "SPOTIFY_REDIRECT_URI",
    "http://127.0.0.1:5000/callback"
)

SPOTIFY_SCOPES = (
    "user-top-read "
    "user-read-recently-played "
    "user-read-private"
)

SPOTIFY_ACCOUNTS_URL = "https://accounts.spotify.com"
SPOTIFY_API_URL = "https://api.spotify.com/v1"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True
)

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    secrets.token_hex(32)
)


def fetch_all(query, params=None):
    with engine.connect() as connection:
        result = connection.execute(
            text(query),
            params or {}
        )
        return [dict(row._mapping) for row in result]


def fetch_one(query, params=None):
    with engine.connect() as connection:
        result = connection.execute(
            text(query),
            params or {}
        )
        row = result.first()
        return dict(row._mapping) if row else {}


def spotify_token_request(data):
    credentials = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    return requests.post(
        f"{SPOTIFY_ACCOUNTS_URL}/api/token",
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        timeout=15
    )


def refresh_spotify_token():
    refresh_token = session.get("spotify_refresh_token")

    if not refresh_token:
        return False

    response = spotify_token_request({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    })

    if not response.ok:
        session.pop("spotify_access_token", None)
        session.pop("spotify_refresh_token", None)
        session.pop("spotify_user", None)
        return False

    token_data = response.json()

    session["spotify_access_token"] = token_data["access_token"]

    if token_data.get("refresh_token"):
        session["spotify_refresh_token"] = token_data["refresh_token"]

    return True


def spotify_get(endpoint, params=None):
    access_token = session.get("spotify_access_token")

    if not access_token:
        return None

    response = requests.get(
        f"{SPOTIFY_API_URL}{endpoint}",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        params=params or {},
        timeout=15
    )

    if response.status_code == 401:
        if refresh_spotify_token():
            access_token = session.get("spotify_access_token")

            response = requests.get(
                f"{SPOTIFY_API_URL}{endpoint}",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                params=params or {},
                timeout=15
            )

    if not response.ok:
        return None

    return response.json()


def chunked(items, size):
    items = list(items)

    for index in range(0, len(items), size):
        yield items[index:index + size]


def fetch_artists_by_ids(artist_ids):
    """
    Fetch artist details individually.

    Spotify removed the batch GET /artists endpoint in the February 2026
    Web API changes. Keep this helper for optional metadata such as genres and
    images, but the actual artist name used by personal analytics is taken
    directly from each recently-played track's artists array.
    """
    artists_map = {}

    unique_ids = [
        artist_id
        for artist_id in dict.fromkeys(artist_ids)
        if artist_id
    ]

    for artist_id in unique_ids:
        response = spotify_get(f"/artists/{artist_id}")

        if not response:
            continue

        artists_map[artist_id] = {
            "name": response.get("name"),
            "genres": response.get("genres", []),
            "image": (
                response.get("images", [{}])[0].get("url")
                if response.get("images")
                else None
            ),
            "spotify_url": response.get(
                "external_urls", {}
            ).get("spotify")
        }

    return artists_map


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/audio/<path:filename>")
def audio(filename):
    return send_from_directory(
        AUDIO_DIR,
        filename,
        mimetype="audio/mpeg"
    )


@app.route("/api/health")
def health():
    try:
        fetch_one("SELECT 1 AS status")

        return jsonify({
            "status": "ok",
            "database": "connected",
            "audio_directory": AUDIO_DIR.exists()
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "database": "disconnected",
            "message": str(error)
        }), 500


@app.route("/api/filters")
def filters():
    artists = fetch_all("""
        SELECT DISTINCT name
        FROM artists
        ORDER BY name
    """)

    return jsonify({
        "artists": [row["name"] for row in artists]
    })


@app.route("/api/dashboard")
def dashboard():
    artist = request.args.get("artist", "All")

    params = {}
    artist_filter = ""

    if artist and artist != "All":
        artist_filter = "AND a.name = :artist"
        params["artist"] = artist

    kpis = fetch_one(f"""
        SELECT
            COUNT(DISTINCT t.id) AS tracks,
            COUNT(DISTINCT a.id) AS artists,
            COUNT(DISTINCT al.id) AS albums
        FROM tracks t
        JOIN artists a
            ON a.id = t.artist_id
        LEFT JOIN albums al
            ON al.id = t.album_id
        WHERE 1=1
        {artist_filter}
    """, params)

    listens = fetch_one(f"""
        SELECT
            COUNT(*) AS total_listens,
            COUNT(DISTINCT lh.track_id) AS unique_tracks
        FROM listening_history lh
        JOIN tracks t
            ON t.id = lh.track_id
        JOIN artists a
            ON a.id = t.artist_id
        WHERE 1=1
        {artist_filter}
    """, params)

    top_artists = fetch_all(f"""
        SELECT
            a.name AS artist,
            COUNT(t.id) AS tracks,
            COUNT(lh.id) AS listens
        FROM artists a
        JOIN tracks t
            ON t.artist_id = a.id
        LEFT JOIN listening_history lh
            ON lh.track_id = t.id
        WHERE 1=1
        {artist_filter}
        GROUP BY a.id, a.name
        ORDER BY listens DESC, tracks DESC
        LIMIT 10
    """, params)

    top_tracks = fetch_all(f"""
        SELECT
            t.name AS track,
            a.name AS artist,
            COUNT(lh.id) AS listens
        FROM tracks t
        JOIN artists a
            ON a.id = t.artist_id
        LEFT JOIN listening_history lh
            ON lh.track_id = t.id
        WHERE 1=1
        {artist_filter}
        GROUP BY t.id, t.name, a.name
        ORDER BY listens DESC, t.name
        LIMIT 10
    """, params)

    albums = fetch_all(f"""
        SELECT
            al.name AS album,
            a.name AS artist,
            COUNT(t.id) AS tracks
        FROM albums al
        JOIN artists a
            ON a.id = al.artist_id
        LEFT JOIN tracks t
            ON t.album_id = al.id
        WHERE 1=1
        {"AND a.name = :artist" if artist and artist != "All" else ""}
        GROUP BY al.id, al.name, a.name
        ORDER BY tracks DESC
        LIMIT 10
    """, params)

    listening_trend = fetch_all(f"""
        SELECT
            TO_CHAR(DATE(lh.played_at), 'YYYY-MM-DD') AS play_date,
            COUNT(*) AS listens
        FROM listening_history lh
        JOIN tracks t
            ON t.id = lh.track_id
        JOIN artists a
            ON a.id = t.artist_id
        WHERE 1=1
        {artist_filter}
        GROUP BY DATE(lh.played_at)
        ORDER BY DATE(lh.played_at)
    """, params)

    feature_summary = fetch_one(f"""
        SELECT
            COUNT(*) AS feature_count,
            ROUND(AVG(tf.energy)::numeric, 3) AS avg_energy,
            ROUND(AVG(tf.danceability)::numeric, 3) AS avg_danceability,
            ROUND(AVG(tf.valence)::numeric, 3) AS avg_valence,
            ROUND(AVG(tf.acousticness)::numeric, 3) AS avg_acousticness,
            ROUND(AVG(tf.tempo)::numeric, 2) AS avg_tempo
        FROM track_features tf
        JOIN tracks t
            ON t.id = tf.track_id
        JOIN artists a
            ON a.id = t.artist_id
        WHERE 1=1
        {artist_filter}
    """, params)

    feature_data = fetch_all(f"""
        SELECT
            t.spotify_track_id,
            t.name AS track,
            a.name AS artist,
            tf.energy,
            tf.danceability,
            tf.valence,
            tf.acousticness,
            tf.tempo,
            COUNT(lh.id) AS listens
        FROM track_features tf
        JOIN tracks t
            ON t.id = tf.track_id
        JOIN artists a
            ON a.id = t.artist_id
        LEFT JOIN listening_history lh
            ON lh.track_id = t.id
        WHERE 1=1
        {artist_filter}
        GROUP BY
            t.spotify_track_id,
            t.name,
            a.name,
            tf.energy,
            tf.danceability,
            tf.valence,
            tf.acousticness,
            tf.tempo
        ORDER BY listens DESC
    """, params)

    for row in feature_data:
        track_id = str(row["spotify_track_id"])
        audio_file = AUDIO_DIR / f"{track_id}.mp3"

        row["audio_available"] = audio_file.exists()

        if row["audio_available"]:
            row["audio_url"] = f"/audio/{track_id}.mp3"
        else:
            row["audio_url"] = None

        row["spotify_url"] = (
            f"https://open.spotify.com/track/{track_id}"
        )

    return jsonify({
        "kpis": {
            "tracks": kpis["tracks"] or 0,
            "artists": kpis["artists"] or 0,
            "albums": kpis["albums"] or 0,
            "listens": listens["total_listens"] or 0,
            "unique_tracks": listens["unique_tracks"] or 0
        },
        "artists": top_artists,
        "tracks": top_tracks,
        "albums": albums,
        "trend": listening_trend,
        "features": {
            "summary": feature_summary,
            "tracks": feature_data
        }
    })


@app.route("/api/tracks")
def tracks():
    artist = request.args.get("artist", "All")
    search = request.args.get("search", "")

    conditions = []
    params = {}

    if artist and artist != "All":
        conditions.append("a.name = :artist")
        params["artist"] = artist

    if search:
        conditions.append("""
            (
                LOWER(t.name) LIKE LOWER(:search)
                OR LOWER(a.name) LIKE LOWER(:search)
                OR LOWER(al.name) LIKE LOWER(:search)
            )
        """)
        params["search"] = f"%{search}%"

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            t.id,
            t.spotify_track_id,
            t.name AS track,
            a.name AS artist,
            al.name AS album,
            TO_CHAR(
                al.release_date::date,
                'YYYY-MM-DD'
            ) AS release_date,
            t.duration_ms,
            COUNT(lh.id) AS listens
        FROM tracks t
        JOIN artists a
            ON a.id = t.artist_id
        LEFT JOIN albums al
            ON al.id = t.album_id
        LEFT JOIN listening_history lh
            ON lh.track_id = t.id
        {where_clause}
        GROUP BY
            t.id,
            t.spotify_track_id,
            t.name,
            a.name,
            al.name,
            al.release_date,
            t.duration_ms
        ORDER BY listens DESC, t.name
    """

    data = fetch_all(query, params)

    return jsonify({
        "count": len(data),
        "tracks": data
    })


@app.route("/login/spotify")
def spotify_login():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return jsonify({
            "status": "error",
            "message": "Spotify client credentials are missing."
        }), 500

    state = secrets.token_urlsafe(32)
    session["spotify_state"] = state

    params = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "scope": SPOTIFY_SCOPES,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "state": state
    }

    authorization_url = (
        f"{SPOTIFY_ACCOUNTS_URL}/authorize?"
        f"{urlencode(params)}"
    )

    return redirect(authorization_url)


@app.route("/callback")
def spotify_callback():
    error = request.args.get("error")

    if error:
        return redirect("/?spotify_error=access_denied")

    state = request.args.get("state")

    if state != session.get("spotify_state"):
        return redirect("/?spotify_error=invalid_state")

    code = request.args.get("code")

    if not code:
        return redirect("/?spotify_error=missing_code")

    response = spotify_token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI
    })

    if not response.ok:
        return redirect("/?spotify_error=token_exchange_failed")

    token_data = response.json()

    session["spotify_access_token"] = token_data["access_token"]

    if token_data.get("refresh_token"):
        session["spotify_refresh_token"] = token_data["refresh_token"]

    session.pop("spotify_state", None)

    profile = spotify_get("/me")

    if profile:
        session["spotify_user"] = {
            "id": profile.get("id"),
            "display_name": profile.get("display_name"),
            "product": profile.get("product"),
            "image": (
                profile.get("images", [{}])[0].get("url")
                if profile.get("images")
                else None
            )
        }

    return redirect("/")


@app.route("/logout/spotify")
def spotify_logout():
    session.pop("spotify_access_token", None)
    session.pop("spotify_refresh_token", None)
    session.pop("spotify_user", None)
    session.pop("spotify_state", None)

    return redirect("/")


@app.route("/api/spotify/status")
def spotify_status():
    access_token = session.get("spotify_access_token")

    if not access_token:
        return jsonify({
            "authenticated": False
        })

    profile = spotify_get("/me")

    if not profile:
        session.pop("spotify_access_token", None)
        session.pop("spotify_refresh_token", None)
        session.pop("spotify_user", None)

        return jsonify({
            "authenticated": False
        })

    user = {
        "id": profile.get("id"),
        "display_name": profile.get("display_name"),
        "product": profile.get("product"),
        "image": (
            profile.get("images", [{}])[0].get("url")
            if profile.get("images")
            else None
        )
    }

    session["spotify_user"] = user

    return jsonify({
        "authenticated": True,
        "user": user
    })


@app.route("/api/spotify/analytics")
def spotify_analytics():
    """
    Builds "Your Spotify" analytics from real account data.

    Important limitation: Spotify's public API does not expose lifetime
    play counts for tracks/artists anywhere. The only endpoint that gives
    real, timestamped listening events is /me/player/recently-played,
    which only returns your latest ~50 plays. So "amount of listening"
    here is computed by actually counting how many times each track /
    artist appears in that recent-plays window - this is real data from
    your account, just scoped to your most recent listening rather than
    all-time totals.
    """

    if not session.get("spotify_access_token"):
        return jsonify({
            "authenticated": False,
            "message": "Connect Spotify first."
        }), 401

    profile = spotify_get("/me")

    if not profile:
        return jsonify({
            "authenticated": False,
            "message": "Spotify session expired."
        }), 401

    recent = spotify_get(
        "/me/player/recently-played",
        {"limit": 50}
    )

    recent_items = recent.get("items", []) if recent else []

    recent_tracks = []
    track_play_counts = Counter()
    artist_play_counts = Counter()
    track_info = {}
    artist_ids_seen = []
    artist_names = {}

    for item in recent_items:
        track = item.get("track") or {}
        track_id = track.get("id")
        artists = track.get("artists") or []
        primary_artist = artists[0] if artists else {}
        artist_id = primary_artist.get("id")
        artist_name = primary_artist.get("name") or "Unknown Artist"
        album = track.get("album") or {}

        album_image = (
            album.get("images", [{}])[0].get("url")
            if album.get("images")
            else None
        )

        recent_tracks.append({
            "name": track.get("name"),
            "artist": artist_name,
            "album": album.get("name"),
            "played_at": item.get("played_at"),
            "spotify_url": track.get(
                "external_urls", {}
            ).get("spotify"),
            "image": album_image
        })

        if track_id:
            track_play_counts[track_id] += 1

            if track_id not in track_info:
                track_info[track_id] = {
                    "name": track.get("name"),
                    "artist": artist_name,
                    "album": album.get("name"),
                    "spotify_url": track.get(
                        "external_urls", {}
                    ).get("spotify"),
                    "image": album_image
                }

        if artist_id:
            artist_play_counts[artist_id] += 1
            artist_names[artist_id] = artist_name

            if artist_id not in artist_ids_seen:
                artist_ids_seen.append(artist_id)

    # The recently-played track object already contains the real artist name.
    # Do not depend on the removed batch GET /artists endpoint for this.
    artists_map = fetch_artists_by_ids(artist_ids_seen)

    top_artists_by_plays = []

    for artist_id, count in artist_play_counts.most_common(10):
        info = artists_map.get(artist_id, {})

        top_artists_by_plays.append({
            "name": artist_names.get(artist_id)
                or info.get("name")
                or "Unknown Artist",
            "plays": count,
            "genres": info.get("genres", []),
            "image": info.get("image"),
            "spotify_url": info.get("spotify_url")
                or f"https://open.spotify.com/artist/{artist_id}"
        })

    top_tracks_by_plays = []

    for track_id, count in track_play_counts.most_common(10):
        info = track_info.get(track_id, {})

        top_tracks_by_plays.append({
            "name": info.get("name", "-"),
            "artist": info.get("artist", "-"),
            "album": info.get("album"),
            "plays": count,
            "spotify_url": info.get("spotify_url"),
            "image": info.get("image")
        })

    genre_play_counts = Counter()

    for artist_id, count in artist_play_counts.items():
        info = artists_map.get(artist_id, {})

        for genre in info.get("genres", []):
            genre_play_counts[genre] += count

    top_genres = [
        {"genre": genre, "plays": count}
        for genre, count in genre_play_counts.most_common(10)
    ]

    unique_recent_tracks = len(track_play_counts)
    unique_recent_artists = len(artist_play_counts)

    top_artist_name = (
        top_artists_by_plays[0]["name"]
        if top_artists_by_plays
        else "-"
    )

    return jsonify({
        "authenticated": True,
        "user": {
            "id": profile.get("id"),
            "display_name": profile.get("display_name"),
            "product": profile.get("product"),
            "image": (
                profile.get("images", [{}])[0].get("url")
                if profile.get("images")
                else None
            )
        },
        "kpis": {
            "recent_plays": len(recent_tracks),
            "unique_recent_tracks": unique_recent_tracks,
            "unique_recent_artists": unique_recent_artists,
            "top_artist": top_artist_name
        },
        "top_artists_by_plays": top_artists_by_plays,
        "top_tracks_by_plays": top_tracks_by_plays,
        "top_genres": top_genres,
        "recent_tracks": recent_tracks
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
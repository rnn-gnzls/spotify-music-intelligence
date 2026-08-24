import os,pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
load_dotenv();engine=create_engine(os.getenv("DATABASE_URL"))
df=pd.read_csv("data/spotify_tracks_raw.csv")
df["release_date"]=pd.to_datetime(df.release_date,errors="coerce")
for c in ["popularity","streams","danceability","energy","valence","acousticness","instrumentalness","speechiness","tempo"]:
    df[c]=pd.to_numeric(df[c],errors="coerce")
df=df.drop_duplicates("track_id").dropna(subset=["track_id","track_name","artist","release_date"])
df=df[df.popularity.between(0,100)&(df.streams>=0)]
df.to_csv("data/spotify_tracks_clean.csv",index=False)
df.to_sql("tracks",engine,if_exists="replace",index=False)
print("Spotify CSV -> cleaned CSV -> PostgreSQL complete.")

DROP TABLE IF EXISTS tracks;

CREATE TABLE tracks (
    track_id VARCHAR(50) PRIMARY KEY,
    track_name VARCHAR(250) NOT NULL,
    artist VARCHAR(200) NOT NULL,
    album VARCHAR(250),
    genre VARCHAR(100),
    release_date DATE,
    popularity INT,
    streams BIGINT,
    danceability NUMERIC(5,4),
    energy NUMERIC(5,4),
    valence NUMERIC(5,4),
    acousticness NUMERIC(5,4),
    instrumentalness NUMERIC(5,4),
    speechiness NUMERIC(5,4),
    tempo NUMERIC(7,2)
);
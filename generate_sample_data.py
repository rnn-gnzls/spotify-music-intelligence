from pathlib import Path
import random,pandas as pd
from datetime import date,timedelta
random.seed(99)
artists=["Hannah Montana","Victorious Cast","Taylor Swift","The Weeknd","Dua Lipa","Billie Eilish","Bruno Mars","Ariana Grande","Ed Sheeran","Olivia Rodrigo"]
genres=["Pop","R&B","Rock","Hip-Hop","Indie Pop","Electronic"]
rows=[]
for i in range(1,1201):
    energy=random.random();dance=random.random();pop=min(100,max(0,int(35+energy*30+dance*20+random.gauss(0,10))))
    rows.append({"track_id":f"T{i:06d}","track_name":f"Track {i:04d}","artist":random.choice(artists),
    "album":f"Album {random.randint(1,4)}","genre":random.choice(genres),
    "release_date":date(2018,1,1)+timedelta(days=random.randint(0,7*365)),
    "popularity":pop,"streams":random.randint(10000,50000000),
    "danceability":round(dance,4),"energy":round(energy,4),"valence":round(random.random(),4),
    "acousticness":round(random.random(),4),"instrumentalness":round(random.random(),4),
    "speechiness":round(random.random()/2,4),"tempo":round(random.uniform(70,180),2)})
Path("data").mkdir(exist_ok=True);pd.DataFrame(rows).to_csv("data/spotify_tracks_raw.csv",index=False)
print("Created 1,200 Spotify-style track records.")

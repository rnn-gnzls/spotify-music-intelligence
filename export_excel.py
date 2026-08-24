import os,pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
load_dotenv();engine=create_engine(os.getenv("DATABASE_URL"))
queries={
"Artist_Analysis":"SELECT artist,COUNT(*) tracks,ROUND(AVG(popularity),2) avg_popularity,ROUND(AVG(streams),0) avg_streams FROM tracks GROUP BY artist ORDER BY avg_streams DESC",
"Genre_Analysis":"SELECT genre,COUNT(*) tracks,ROUND(AVG(popularity),2) avg_popularity,ROUND(AVG(streams),0) avg_streams FROM tracks GROUP BY genre ORDER BY avg_streams DESC",
"Popularity_Trend":"SELECT DATE_TRUNC('year',release_date)::date year,ROUND(AVG(popularity),2) avg_popularity,ROUND(AVG(streams),0) avg_streams,COUNT(*) tracks FROM tracks GROUP BY 1 ORDER BY 1",
"Energy_Analysis":"SELECT CASE WHEN energy>=.70 THEN 'High Energy' WHEN energy>=.40 THEN 'Medium Energy' ELSE 'Low Energy' END energy_group,COUNT(*) tracks,ROUND(AVG(streams),0) avg_streams,ROUND(AVG(popularity),2) avg_popularity FROM tracks GROUP BY 1",
"Track_Detail":"SELECT * FROM tracks ORDER BY streams DESC"}
with pd.ExcelWriter("spotify_music_analytics.xlsx",engine="openpyxl") as w:
    for s,sql in queries.items():pd.read_sql(sql,engine).to_excel(w,sheet_name=s,index=False)
print("Created spotify_music_analytics.xlsx")

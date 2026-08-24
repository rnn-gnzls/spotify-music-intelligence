import os,pandas as pd
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv();

app=Flask(__name__);
engine=create_engine(os.getenv("DATABASE_URL"))

def q(sql,params=None):
    with engine.connect() as c:return pd.read_sql(text(sql),c,params=params or {})

@app.route("/")
def home():return render_template("index.html")

@app.route("/api/filters")
def filters():return jsonify({"artists":q(
    "SELECT DISTINCT artist FROM tracks ORDER BY artist")["artist"].tolist(),
    "genres":q("SELECT DISTINCT genre FROM tracks ORDER BY genre")["genre"].tolist()})

@app.route("/api/dashboard")
def dash():
    artist=request.args.get("artist","All");genre=request.args.get("genre","All");cond=[];params={}

    if artist!="All":cond.append("artist=:artist"); 
    params["artist"]=artist

    if genre!="All":cond.append("genre=:genre"); 
    params["genre"]=genre

    w=(" WHERE "+" AND ".join(cond)) if cond else ""

    k=q(f"""SELECT COUNT(*) tracks, COUNT(DISTINCT artist) artists, ROUND(AVG(popularity),2) 
    avg_popularity, ROUND(AVG(streams),0) avg_streams FROM tracks{w}""", params).iloc[0].to_dict()

    a=q(f"""SELECT artist,COUNT(*) tracks,ROUND(AVG(streams),0) streams FROM tracks{w} 
    GROUP BY artist ORDER BY streams DESC LIMIT 10""", params)

    g=q(f"""SELECT genre,ROUND(AVG(streams),0) streams FROM tracks{w} 
    GROUP BY genre ORDER BY streams DESC""", params)

    t=q(f"""SELECT TO_CHAR(DATE_TRUNC('year',release_date),'YYYY') year, ROUND(AVG(popularity),2) 
    popularity FROM tracks{w} GROUP BY 1 ORDER BY 1""", params)

    e=q(f"""SELECT CASE WHEN energy>=.70 THEN 'High Energy' WHEN energy>=.40 THEN 'Medium Energy' 
    ELSE 'Low Energy' END energy_group, ROUND(AVG(streams),0) streams FROM tracks{w} 
    GROUP BY 1 ORDER BY 1""", params)

    return jsonify(
        { "kpis":k,"artists":a.to_dict("records"), "genres":g.to_dict("records"), 
         "trend":t.to_dict("records"),"energy":e.to_dict("records")
        })

app.run( debug=True, port=5003 )
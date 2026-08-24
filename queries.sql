-- Do energetic songs receive more streams?
SELECT CASE WHEN energy>=.70 THEN 'High Energy'
WHEN energy>=.40 THEN 'Medium Energy' ELSE 'Low Energy' END energy_group,
COUNT(*) tracks,ROUND(AVG(streams),0) avg_streams,ROUND(AVG(popularity),2) avg_popularity
FROM tracks GROUP BY 1 ORDER BY 1;

-- Artists with consistent popularity
SELECT artist,COUNT(*) tracks,ROUND(AVG(popularity),2) avg_popularity,
ROUND(AVG(streams),0) avg_streams,ROUND(STDDEV(popularity),2) popularity_stddev
FROM tracks GROUP BY artist HAVING COUNT(*)>=5 ORDER BY avg_popularity DESC;

-- Popularity through time
SELECT DATE_TRUNC('year',release_date)::date year,ROUND(AVG(popularity),2) avg_popularity,
ROUND(AVG(streams),0) avg_streams,COUNT(*) tracks
FROM tracks GROUP BY 1 ORDER BY 1;

-- Genre performance
SELECT genre,COUNT(*) tracks,ROUND(AVG(popularity),2) avg_popularity,
ROUND(AVG(streams),0) avg_streams FROM tracks GROUP BY genre ORDER BY avg_streams DESC;

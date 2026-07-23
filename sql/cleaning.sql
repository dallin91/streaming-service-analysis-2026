-- Run this after running create_tables.sql

DROP TABLE IF EXISTS titles_clean;

CREATE TABLE titles_clean AS
SELECT service, id, title, CASE WHEN LOWER(type) LIKE '%movie%' THEN 'movie'
WHEN LOWER(type) LIKE '%tv%' THEN 'tv_shows' ELSE 'other' END AS type_clean, year, genre_names, user_rating, critic_score, imdb_id, tmdb_id, us_rating
FROM raw_titles
WHERE service IS NOT NULL AND title IS NOT NULL;

DROP TABLE IF EXISTS service_title_counts;

CREATE TABLE service_title_counts AS
SELECT service, COUNT(*) FILTER (WHERE type_clean = 'movie') AS movie_count, COUNT(*) FILTER (WHERE type_clean = 'tv_show') AS tv_show_count,
COUNT(*) AS total_title_count, ROUND(AVG(user_rating), 2) AS avg_user_rating, ROUND(AVG(critic_score), 2) AS avg_critic_score
FROM titles_clean
GROUP BY service;
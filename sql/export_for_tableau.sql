-- Run this after analysis.sql
-- This the purpose of this is to export the 4 views created in analysis.sql to .csv files to be used in Tableau

\copy (SELECT * FROM service_avg_scores) TO 'data/tableau/service_avg_scores.csv' WITH CSV HEADER ENCODING 'utf8'

\copy (SELECT * FROM service_genre_avg_scores) TO 'data/tableau/service_genre_avg_scores.csv' WITH CSV HEADER ENCODING 'utf8'

\copy (SELECT * FROM service_avg_scores_per_dollar) TO 'data/tableau/service_avg_scores_per_dollar.csv' WITH CSV HEADER ENCODING 'utf8'

\copy (SELECT * FROM service_genre_avg_scores_per_dollar) TO 'data/tableau/service_genre_avg_scores_per_dollar.csv' WITH CSV HEADER ENCODING 'utf8'
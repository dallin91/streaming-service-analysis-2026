DROP TABLE IF EXISTS raw_titles;
DROP TABLE IF EXISTS pricing;

CREATE TABLE raw_titles (
    service     TEXT,
    id    INTEGER,
    title       TEXT,
    type  TEXT,
    year    INTEGER,
    genre_names     TEXT,
    user_rating     NUMERIC,
    critic_score    NUMERIC,
    imdb_id     TEXT,
    tmdb_id     INTEGER,
    us_rating   TEXT
);

CREATE TABLE pricing (
    service     TEXT,
    plan_name   TEXT,
    has_ads     BOOLEAN,
    monthly_price_usd       NUMERIC
);

\copy raw_titles (service, id, title, type, year, genre_names, user_rating, critic_score, imdb_id, tmdb_id, us_rating) FROM 'data/raw/streaming_titles_raw.csv' WITH CSV HEADER

\copy pricing (service, plan_name, has_ads, monthly_price_usd) FROM 'data/pricing/streaming_services_pricing.csv' WITH CSV HEADER
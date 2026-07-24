-- Run this after running create_tables.sql

-- Let's start by normalizing service names between the tables
UPDATE raw_titles
SET service = 'Prime Video'
WHERE service = 'Amazon Prime Video';

UPDATE pricing
SET service = 'Max'
WHERE service = 'HBO Max';

-- I'm going to delete any plans with a limited library because I'm not interested in a limited library
DELETE FROM pricing
WHERE plan_name LIKE '%limited library%';

DROP TABLE IF EXISTS pricing_wide;

-- A little reshaping of the pricing table to get each service down to just one row as a new table 
CREATE TABLE pricing_wide
AS
SELECT service, 
MAX(CASE WHEN has_ads = false THEN monthly_price_usd END) AS adfree_price,
MIN(CASE WHEN has_ads = true THEN monthly_price_usd END) AS adsupported_price
FROM pricing
GROUP BY service;

DROP TABLE IF EXISTS title_genres;

-- The raw_titles table has a genre column that is a bit messy. Let's split that out into it's own table
CREATE TABLE title_genres
AS
SELECT id, unnest(string_to_array(genre_names, '|')) AS genre
FROM raw_titles;

-- Consolidate genres where needed
UPDATE title_genres
SET genre = CASE genre
WHEN 'Action' THEN 'Action & Adventure'
WHEN 'Adventure' THEN 'Action & Adventure'
WHEN 'Science Fiction' THEN 'Sci-Fi & Fantasy'
WHEN 'Fantasy' THEN 'Sci-Fi & Fantasy'
WHEN 'War' THEN 'War & Politics'
WHEN 'Kids' THEN 'Family'
WHEN 'Crime' THEN 'Crime & Mystery'
WHEN 'Mystery' THEN 'Crime & Mystery'
END
WHERE genre IN ('Action','Adventure','Science Fiction','Fantasy','War','Kids','Crime','Mystery');

-- Delete the TV Movie genre as that isn't really a genre
DELETE FROM title_genres
WHERE genre = 'TV Movie';

-- With the genre consolidation, I need to get rid of duplicate lines. This will create a new temporary table, drop title_genres, 
-- and rename the new table to title_genres
CREATE TABLE title_genres_temporary
AS
SELECT DISTINCT id, genre
FROM title_genres;
DROP TABLE title_genres;
ALTER TABLE title_genres_temporary
RENAME TO title_genres;

DROP TABLE IF EXISTS titles_with_pricing;

-- Join raw_titles with pricing_wide. This new table will be the base for further analysis, along with title_genres
CREATE TABLE titles_with_pricing
AS
SELECT id, title, pricing_wide.service, type, year, user_rating, critic_score, us_rating, adfree_price, adsupported_price
FROM pricing_wide 
JOIN raw_titles ON raw_titles.service = pricing_wide.service;
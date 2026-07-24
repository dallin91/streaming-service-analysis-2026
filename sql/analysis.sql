-- Run this file after running cleaning.sql

-- First let's look at the average user/critic ratings broken down by service
DROP VIEW IF EXISTS service_avg_scores;
CREATE VIEW service_avg_scores
AS
SELECT service, ROUND(AVG(user_rating), 2) AS avg_user_rating, ROUND(AVG(critic_score), 2) AS avg_critic_score
FROM titles_with_pricing
GROUP BY service
ORDER BY AVG(user_rating) desc;

-- Now let's drill down deeper by breaking it into genres
DROP VIEW IF EXISTS service_genre_avg_scores;
CREATE VIEW service_genre_avg_scores
AS
SELECT service, title_genres.genre, COUNT(*) AS total_num_titles, ROUND(AVG(user_rating), 2) AS avg_user_rating, ROUND(AVG(critic_score), 2) AS avg_critic_score 
FROM titles_with_pricing
LEFT JOIN title_genres ON title_genres.id = titles_with_pricing.id
GROUP BY service, genre
ORDER BY AVG(user_rating) desc;

-- Attempting to quantify value based on average user rating per dollar
DROP VIEW IF EXISTS service_avg_scores_per_dollar;
CREATE VIEW service_avg_scores_per_dollar
AS
SELECT service, ROUND(AVG(user_rating), 2) AS avg_user_rating, ROUND(AVG(critic_score), 2) AS avg_critic_score, MAX(adfree_price) AS adfree_price,
ROUND(AVG(user_rating)/MAX(adfree_price), 2) AS user_rating_per_dollar
FROM titles_with_pricing
GROUP BY service
ORDER BY AVG(user_rating)/MAX(adfree_price) desc;

-- Now doing the same as before and drilling deeper into genres
DROP VIEW IF EXISTS service_genre_avg_scores_per_dollar;
CREATE VIEW service_genre_avg_scores_per_dollar
AS
SELECT service, title_genres.genre, COUNT(*) AS total_num_titles, ROUND(AVG(user_rating), 2) AS avg_user_rating, ROUND(AVG(critic_score), 2) AS avg_critic_score, MAX(adfree_price) AS adfree_price,
ROUND(AVG(user_rating)/MAX(adfree_price), 2) AS user_rating_per_dollar
FROM titles_with_pricing
LEFT JOIN title_genres ON title_genres.id = titles_with_pricing.id
GROUP BY service, genre
ORDER BY AVG(user_rating)/MAX(adfree_price) desc;
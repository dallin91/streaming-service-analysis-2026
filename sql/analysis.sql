-- Run this file after running cleaning.sql

-- First let's look at the average user/critic ratings broken down by service
SELECT service, ROUND(AVG(user_rating), 2) AS avg_user_rating, ROUND(AVG(critic_score), 2) AS avg_critic_score
FROM titles_with_pricing
GROUP BY service
ORDER BY AVG(user_rating) desc;

-- Now let's drill down deeper by breaking it into genres
SELECT service, title_genres.genre, COUNT(*) AS total_num_titles, ROUND(AVG(user_rating), 2) AS avg_user_rating, ROUND(AVG(critic_score), 2) AS avg_critic_score 
FROM titles_with_pricing
LEFT JOIN title_genres ON title_genres.id = titles_with_pricing.id
GROUP BY service, genre
ORDER BY AVG(user_rating) desc;
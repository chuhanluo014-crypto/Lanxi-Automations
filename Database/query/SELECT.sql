SELECT 
  COUNT(*) AS total,
  SUM(keep_status = '保留') AS keep_count,
  SUM(keep_status = '降权') AS down_count
FROM xhs_samples;

SELECT topic, COUNT(*) AS count, AVG(likes) AS avg_likes, AVG(collects) AS avg_collects
FROM xhs_samples
WHERE keep_status = '保留'
GROUP BY topic
ORDER BY count DESC;

SELECT emotion, COUNT(*) AS count, AVG(likes) AS avg_likes
FROM xhs_samples
WHERE keep_status = '保留'
GROUP BY emotion
ORDER BY count DESC;

SELECT reusable_structure, COUNT(*) AS count, AVG(likes) AS avg_likes
FROM xhs_samples
WHERE keep_status = '保留'
GROUP BY reusable_structure
ORDER BY count DESC;

SELECT id, title, likes, collects, topic, emotion, reusable_structure
FROM xhs_samples
WHERE keep_status = '保留'
ORDER BY likes DESC, collects DESC
LIMIT 30;
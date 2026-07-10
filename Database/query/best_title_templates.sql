-- 什么标题模板互动最好？
SELECT
    title_template,
    COUNT(*) AS sample_count,
    ROUND(AVG(engagement_score), 4) AS avg_engagement_score,
    SUM(likes) AS total_likes,
    SUM(comments) AS total_comments,
    SUM(collects) AS total_collects
FROM xhs_ip_lab.xhs_text_features
WHERE keep_status = _utf8mb4'保留'
GROUP BY title_template
ORDER BY avg_engagement_score DESC;

-- 哪些平台关键词更适合蓝汐？
SELECT
    platform_keywords,
    COUNT(*) AS sample_count,
    ROUND(AVG(engagement_score), 4) AS avg_engagement_score,
    SUM(collects) AS total_collects
FROM xhs_ip_lab.xhs_text_features
WHERE keep_status = _utf8mb4'保留'
  AND risk_level = _utf8mb4'低'
GROUP BY platform_keywords
ORDER BY avg_engagement_score DESC, total_collects DESC;

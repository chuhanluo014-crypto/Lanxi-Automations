-- 蓝汐后续发帖应该优先复用哪些结构？
SELECT
    content_structure,
    COUNT(*) AS sample_count,
    ROUND(AVG(engagement_score), 4) AS avg_engagement_score,
    ROUND(AVG(collects), 2) AS avg_collects,
    SUM(collects) AS total_collects
FROM xhs_ip_lab.xhs_text_features
WHERE keep_status = _utf8mb4'保留'
  AND risk_level = _utf8mb4'低'
GROUP BY content_structure
ORDER BY avg_engagement_score DESC, avg_collects DESC, sample_count DESC;

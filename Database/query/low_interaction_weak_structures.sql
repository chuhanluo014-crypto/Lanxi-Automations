-- 低互动样本是不是某些结构不适合蓝汐？
SELECT
    content_structure,
    COUNT(*) AS low_interaction_count,
    ROUND(AVG(engagement_score), 4) AS avg_engagement_score,
    ROUND(AVG(collects), 2) AS avg_collects
FROM xhs_ip_lab.xhs_text_features
WHERE keep_status = _utf8mb4'保留'
  AND engagement_level = _utf8mb4'低互动'
GROUP BY content_structure
ORDER BY low_interaction_count DESC, avg_engagement_score ASC;

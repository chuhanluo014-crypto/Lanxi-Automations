-- 高收藏样本集中在哪些痛点？
SELECT
    pain_point,
    COUNT(*) AS sample_count,
    ROUND(AVG(collects), 2) AS avg_collects,
    SUM(collects) AS total_collects
FROM xhs_ip_lab.xhs_text_features
WHERE keep_status = _utf8mb4'保留'
GROUP BY pain_point
ORDER BY avg_collects DESC, total_collects DESC;

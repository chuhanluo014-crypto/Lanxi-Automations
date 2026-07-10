-- 什么痛点最多？
SELECT pain_point, COUNT(*) AS count
FROM xhs_ip_lab.xhs_text_features
WHERE keep_status = _utf8mb4'保留'
GROUP BY pain_point
ORDER BY count DESC;

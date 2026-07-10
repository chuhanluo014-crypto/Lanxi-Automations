-- 高互动样本常见什么标题模板？
SELECT
    title_template,
    COUNT(*) AS count
FROM xhs_ip_lab.xhs_text_features
WHERE keep_status = _utf8mb4'保留'
  AND engagement_level = _utf8mb4'高互动'
GROUP BY title_template
ORDER BY count DESC;

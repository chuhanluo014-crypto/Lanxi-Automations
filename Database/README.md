# XHS IP Lab 本地 MySQL 数据库

这个文件夹是 W4/W5 的数据库与特征工程交付物，用来把小红书样本池、人工标注结果、图片本地路径和文本特征写入本地 MySQL。

更完整的采集、清洗、标注、入库和特征工程流程见：

```text
Database/fixed_process.md
```

## 1. 当前状态

```text
数据库：xhs_ip_lab
样本表：xhs_samples
样本数：490
特征表：xhs_text_features
特征数：490
MySQL 用户：xhs_user
当前密码：本地自定，不入库；如需创建用户，复制 `USER.example.sql` 为 `USER.sql` 后填入本地密码
```

当前样本状态：

```text
review_status：已确认 490
keep_status：保留 424，降权 66
```

`id` 从 36 开始是正常的，因为数据库里的 `id` 是从 CSV 原样导入的，不是 MySQL 自动重新编号。前面的编号空洞来自之前的数据清洗、删除或剔除。

## 2. 文件说明

```text
init_mysql.sql
创建数据库 xhs_ip_lab 和样本表 xhs_samples。

USER.sql
创建导入脚本使用的 MySQL 用户 xhs_user。

import_xhs_samples.py
读取 xhs_sample_pool_v1.csv，并 upsert 到 xhs_samples。

import_xhs_features.py
读取 xhs_text_features_v1.csv，自动创建并 upsert 到 xhs_text_features。

fixed_process.md
完整固定流程文档。

pipeline/append_raw_to_pool.py
把 Easy Scraper JSON 追加到标准样本池 CSV。

pipeline/xhs_data_processing.ipynb
清洗样本池数据。

pipeline/download_images.py
下载封面图并回填 local_image_path。

pipeline/validate_sample_pool.py
入库前质量检查。

pipeline/feature_pipeline.py
生成文本特征 CSV。

query/
常用 SQL 分析查询文件。

Datapool/
样本池、原始采集 JSON、本地图片、字段字典、标注规范和特征 CSV。
```

## 3. 样本池导入 MySQL

标准样本池：

```text
Database/Datapool/data-pool/xhs_sample_pool_v1.csv
```

导入命令：

```powershell
D:\python\python.exe D:\codex\project-001\Database\import_xhs_samples.py --user xhs_user
```

成功输出类似：

```text
Import completed: 490 rows -> xhs_ip_lab.xhs_samples
```

这个脚本使用 upsert 逻辑：如果同一个 `id` 已经存在，会更新旧记录，不会重复插入。

## 4. 文本特征工程

生成特征 CSV：

```powershell
D:\python\python.exe D:\codex\project-001\Database\pipeline\feature_pipeline.py
```

输出文件：

```text
Database/Datapool/features/xhs_text_features_v1.csv
```

导入特征表：

```powershell
D:\python\python.exe D:\codex\project-001\Database\import_xhs_features.py --user xhs_user
```

成功输出类似：

```text
Import completed: 490 rows -> xhs_ip_lab.xhs_text_features
```

`xhs_text_features.sample_id` 通过外键关联 `xhs_samples.id`。如果特征 CSV 中出现主样本表不存在的 `sample_id`，导入会失败，避免产生孤立数据。

## 5. 验证数据库

样本表行数：

```powershell
mysql --default-character-set=utf8mb4 -u xhs_user -p -h 127.0.0.1 xhs_ip_lab -e "SELECT COUNT(*) AS sample_count FROM xhs_samples;"
```

特征表行数：

```powershell
mysql --default-character-set=utf8mb4 -u xhs_user -p -h 127.0.0.1 xhs_ip_lab -e "SELECT COUNT(*) AS feature_count FROM xhs_text_features;"
```

审核状态：

```sql
SELECT review_status, COUNT(*) AS count
FROM xhs_samples
GROUP BY review_status;
```

保留状态：

```sql
SELECT keep_status, COUNT(*) AS count
FROM xhs_samples
GROUP BY keep_status;
```

特征孤立检查：

```sql
SELECT COUNT(*) AS orphan_features
FROM xhs_text_features f
LEFT JOIN xhs_samples s ON f.sample_id = s.id
WHERE s.id IS NULL;
```

目标结果：

```text
sample_count = 490
feature_count = 490
orphan_features = 0
```

## 6. 常用分析查询

查询文件放在：

```text
Database/query/
```

当前已固定的查询包括：

```text
pain_point_counts.sql
best_title_templates.sql
lanxi_platform_keywords.sql
high_collect_structures.sql
priority_reusable_structures.sql
high_interaction_title_templates.sql
high_collect_pain_points.sql
low_interaction_weak_structures.sql
```

这些文件已经改成单条 `SELECT`，并使用完整表名：

```sql
FROM xhs_ip_lab.xhs_text_features
```

这样在 SQLTools 中全选运行时，不会因为 `USE` 或 `SET NAMES` 这类无结果语句导致结果页显示 `No data`。

## 7. 初始化数据库

如果以后需要重新初始化数据库，先进入 MySQL：

```powershell
mysql -u root -p
```

输入 root 密码后，在 MySQL 里执行：

```sql
SOURCE D:/codex/project-001/Database/init_mysql.sql;
```

注意：不要在 PowerShell 里直接用下面这种写法：

```powershell
mysql -u root -p < D:\codex\project-001\Database\init_mysql.sql
```

PowerShell 不支持这种 `<` 输入重定向，会报 `RedirectionNotSupported`。

## 8. 创建数据库用户

如果 `xhs_user` 不能登录，先复制 `Database/USER.example.sql` 为本地文件 `Database/USER.sql`，把 `your_password` 改成你的本机密码，再在 MySQL 里运行：

```sql
SOURCE D:/codex/project-001/Database/USER.sql;
```

`USER.sql` 当前会创建两个来源的用户：

```text
xhs_user@localhost
xhs_user@127.0.0.1
```

密码只保存在本地 `USER.sql`，不要提交到 GitHub。

这样做是为了避免 MySQL 把 `localhost` 和 `127.0.0.1` 当成不同来源时出现权限问题。

## 9. 密码输入方式

可以不在命令里写 `--password`：

```powershell
D:\python\python.exe D:\codex\project-001\Database\import_xhs_samples.py --user xhs_user
```

它会提示：

```text
MySQL password for xhs_user@127.0.0.1:
```

输入密码时终端不会显示任何字符，也不会显示星号。这是正常现象。输入你的本地 MySQL 密码后按 Enter 即可。

也可以用环境变量：

```powershell
$env:MYSQL_PASSWORD="your_password"
D:\python\python.exe D:\codex\project-001\Database\import_xhs_samples.py --user xhs_user
```

## 10. 常见问题

### 为什么 SQLTools 不显示 Query OK？

SQLTools 有时不会显示明显的 `Query OK`，而是打开一个结果页。只要没有红色报错，并且表里能看到数据，就说明执行结果是有效的。

### 为什么全选 SQL 文件运行显示 No data？

如果文件里同时包含 `USE`、`SET NAMES` 和 `SELECT`，SQLTools 可能先展示前两条无结果语句的结果页，让你误以为查询没有数据。

当前 `Database/query/` 里的查询文件已经改成单条 `SELECT`，可以直接全选运行。

### 为什么中文条件可能查不到？

如果工具没有按 `utf8mb4` 发送中文字符串，`WHERE keep_status = '保留'` 可能匹配不到。

当前查询文件使用这种写法：

```sql
WHERE keep_status = _utf8mb4'保留'
```

可以降低中文字符集不一致导致的查询失败。

### USER.sql 还有什么用？

`USER.sql` 是创建用户和授权用的本地文件。现在 `xhs_user` 已经可以导入数据，平时不需要重复运行。以后如果重装 MySQL 或用户丢失，从 `USER.example.sql` 复制一份本地 `USER.sql`，填入本机密码后再运行。

## 11. 设计说明

图片文件不直接存进 MySQL。数据库只保存 `local_image_path`，图片本体继续放在：

```text
Database/Datapool/data-images/
```

当前阶段采用两张核心表：

```text
xhs_samples：标准样本与人工标注
xhs_text_features：规则版文本特征
```

后续如果进入更复杂的数据分析，再考虑拆分作者表、标签表、图片表、发布反馈表和内容生成表。

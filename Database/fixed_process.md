# 小红书样本采集到 MySQL 落库固定流程

本文档说明从 Easy Scraper 采集小红书数据，到样本清洗、标注、图片本地化、最终写入 MySQL 的固定流程。

当前目标不是把原始爬虫数据直接塞进数据库，而是建立一条稳定的数据链路：

```text
Easy Scraper 原始数据
→ 原始文件归档
→ 追加到标准样本池 CSV
→ 数据清洗
→ 图片下载与 local_image_path 回填
→ 标注与人工确认
→ 导入 MySQL
→ SQL 分析与内容策略生成
```

## 0. 当前目录结构

核心目录：

```text
D:/codex/project-001/Database
```

关键文件：

```text
Database/
├── init_mysql.sql
├── User.sql
├── import_xhs_samples.py
├── README.md
├── fixed_process.md
├── pipeline/
│   ├── append_raw_to_pool.py
│   ├── download_images.py
│   ├── rule_prelabel.py
│   ├── xhs_data_processing.ipynb
│   └── validate_sample_pool.py
└── Datapool/
    ├── data-collection/
    ├── data-images/
    ├── data-pool/
    │   ├── xhs_sample_pool_v1.csv
    │   ├── xhs_sample_pool_v1_dictionary.csv
    │   ├── xhs_sample_pool_annotation.xlsx
    │   └── xhs_sample_annotation_guideline_v1.md
```

MySQL 当前状态：

```text
数据库：xhs_ip_lab
数据表：xhs_samples
当前样本数：490
MySQL 用户：xhs_user
密码：本地自定，不入库；如需创建用户，复制 `USER.example.sql` 为 `USER.sql` 后填入本地密码
```

## 1. Easy Scraper 采集

使用 Chrome 扩展 Easy Scraper 采集小红书官网数据。

建议采集字段至少包含：

```text
笔记链接
标题
正文/描述
作者昵称
作者主页链接
点赞数
收藏数
评论数
发布时间
封面图片链接
标签
```

Easy Scraper 以后固定导出 `json`，并且字段结构固定为当前 `6.json` 的格式。

固定字段包括：

```text
note-slider-img src
username
name href
title
desc
date
total
like-wrapper
collect-wrapper
chat-wrapper
comment-inner-container
cover href
```

不再把 Easy Scraper 的 CSV 作为固定输入格式。这样可以减少字段映射分支，降低后续采集落库时的出错概率。


## 2. 原始文件归档

采集完成后，把原始文件放入：

```text
D:/codex/project-001/Database/Datapool/data-collection
```

命名规则建议：

```text
7.json
8.json
9.json
```


原则：

- 原始文件不要手动改。
- 原始文件作为证据留档。
- 后续所有清洗、标注、入库都从副本或样本池文件继续处理。

## 3. 原始数据追加到标准样本池

标准样本池文件是：

```text
D:/codex/project-001/Database/Datapool/data-pool/xhs_sample_pool_v1.csv
```

MySQL 导入脚本只认这个标准样本池结构，不直接认 Easy Scraper 原始文件。

当前标准字段是：

```text
id
note_id
url
title
content
author_id
author_name
likes
comments
collects
tags
images
local_image_path
scraped_at
media_type
push_time
topic
scene
emotion
hook
reusable_structure
risk_level
keep_status
notes
review_status
```

原始数据追加时需要做这些事情：

```text
1. 读取新的 json，格式必须与 6.json 一致
2. 提取 note_id
3. 提取 url
4. 映射 title/content/author/likes/comments/collects/tags/images/push_time
5. 和现有 CSV 按 url 或 note_id 去重
6. 给新增样本分配新的 id
7. 标注字段先留空
8. review_status 先填 待审核
```

这一步现在已经固定为脚本：

```text
D:/codex/project-001/Database/pipeline/append_raw_to_pool.py
```

先 dry-run 预览，不写入 CSV：

```powershell
D:\python\python.exe D:\codex\project-001\Database\pipeline\append_raw_to_pool.py D:\codex\project-001\Database\Datapool\data-collection\7.json --dry-run
```

确认输出中的 `appended`、`skipped_duplicate`、`skipped_invalid` 和 `id_range` 没问题后，再正式写入：

```powershell
D:\python\python.exe D:\codex\project-001\Database\pipeline\append_raw_to_pool.py D:\codex\project-001\Database\Datapool\data-collection\7.json
```


脚本输出示例：

```text
append_raw_to_pool completed
pool_path: D:\codex\project-001\Database\Datapool\data-pool\xhs_sample_pool_v1.csv
input_files: 1
raw_total: 110
appended: 0
skipped_duplicate: 100
skipped_invalid: 10
dry_run: True
```

字段规则：

```text
支持输入：只支持与 6.json 字段结构一致的 Easy Scraper JSON
不再支持 Easy Scraper CSV
不再兼容旧采集字段 author-wrapper、bottom-container
去重依据：url / note_id
新增 id：从当前样本池最大 id 继续递增
新增标注字段：先留空
review_status：自动填 待审核
```

## 4. 数据清洗

清洗文件：

```text
D:/codex/project-001/Database/pipeline/xhs_data_processing.ipynb
```

在 VS Code 中打开这个 notebook，按顺序运行全部 cell。

当前 notebook 已包含的清洗逻辑：

```text
1. 自动定位 xhs_sample_pool_v1.csv
2. 删除 images 为空的样本
3. 删除 keep_status 为 剔除 的样本
4. 删除不需要的旧列，例如 videos、author_avatar、cover_type、shares
5. 清洗 title
   - 只做首尾空白和基础空格规范化
   - 不再删除 emoji、表情符号或颜文字
6. 清洗 content
   - 从 content 中提取 #标签，合并写入 tags 列
   - 从 content 中删除已经提取出的 #标签
   - 去除换行符
   - 换行替换为两个空格
   - 去除类似“原创IP 禁抄袭 禁二改”的说明文本
   - 如果正文全是标签，则置为空
7. 清洗 push_time
   - 统一为 YYYY/MM/DD
   - 删除“编辑于”
   - 删除浙江、福建等 IP 属地
   - 按 2026-06-18 作为锚点处理“昨天”“4天前”等相对日期
```

运行方式：

```text
VS Code 打开 xhs_data_processing.ipynb
→ 点击 Run All
→ 确认没有报错
→ 确认输出中显示样本池路径正确
```

清洗完成后，会直接覆盖保存：

```text
D:/codex/project-001/Database/Datapool/data-pool/xhs_sample_pool_v1.csv
```

## 5. 图片下载与 local_image_path 回填

数据库不直接保存图片文件。

固定规则是：

```text
图片文件保存到 data-images
CSV 和 MySQL 中只保存 local_image_path
```

图片目录：

```text
D:/codex/project-001/Database/Datapool/data-images
```

标准路径格式：

```text
data-images/377_696a1388000000000e03c9e7.webp
```

这一步要完成：

```text
1. 读取新增样本的 images 链接
2. 下载封面图片
3. 用 id + note_id 命名图片
4. 保存到 data-images
5. 把相对路径写回 local_image_path
6. 检查 local_image_path 对应的文件是否真实存在
```

这一步现在已经固定为脚本：

```text
D:/codex/project-001/Database/pipeline/download_images.py
```

先 dry-run，查看有多少条需要下载：

```powershell
D:\python\python.exe D:\codex\project-001\Database\pipeline\download_images.py --dry-run
```

正式下载并回填 `local_image_path`：

```powershell
D:\python\python.exe D:\codex\project-001\Database\pipeline\download_images.py
```

如果只想处理某一批新增 id，例如 `468-520`：

```powershell
D:\python\python.exe D:\codex\project-001\Database\pipeline\download_images.py --ids 468-520 --dry-run
D:\python\python.exe D:\codex\project-001\Database\pipeline\download_images.py --ids 468-520
```

脚本规则：

```text
默认只处理 local_image_path 为空或本地文件不存在的样本。
不会重复下载已经存在的图片。
图片命名格式为 id_note_id.webp/jpg/png。
写回 CSV 的路径为 data-images/文件名。
如需强制重下，使用 --overwrite。
```

## 6. 标注流程

标注规范文件：

```text
D:/codex/project-001/Database/Datapool/data-pool/xhs_sample_annotation_guideline_v1.md
```

主要标注字段：

```text
topic
scene
emotion
hook
reusable_structure
risk_level
keep_status
notes
review_status
```

`notes` 固定约束：

```text
notes 只放“依据：……”内容。
不要写“已确认”。
不要写“预标注”。
不要写“待人工审核”。
不要写“可借鉴：……”。
不要写“注意：……”。
审核状态只写在 review_status，不写进 notes。
```

标注原则：

```text
topic：这条笔记属于什么主题
scene：适合什么使用/发布场景
emotion：主要情绪
hook：吸引互动或收藏的钩子
reusable_structure：可复用的内容结构
risk_level：发布风险，低/中/高
keep_status：保留/降权/剔除
notes：只保留“依据：……”内容
review_status：待审核/已确认
```

推荐流程：

```text
新增样本先由 Codex 按标注规范做预标注
→ review_status 填 待审核
→ 人工看标题、正文、封面图
→ 修改不准确的字段
→ 确认后把 review_status 改为 已确认
```

Codex 预标注任务说明：

```text
触发时机：新增样本已追加到 xhs_sample_pool_v1.csv，且已完成清洗、图片下载和 local_image_path 回填。

输入材料：
1. xhs_sample_pool_v1.csv 中新增样本的 title、content、tags、author_name、likes、comments、collects。
2. local_image_path 指向的本地封面图。
3. xhs_sample_annotation_guideline_v1.md 标注规范。
4. 蓝汐角色档案和现有已确认样本的标注分布。

Codex 要填写：
topic
scene
emotion
hook
reusable_structure
risk_level
keep_status
notes
review_status

输出要求：
1. 新增样本必须补齐 topic、scene、emotion、hook、reusable_structure、risk_level、keep_status。
2. notes 只允许写“依据：……”内容，不写“已确认”“预标注”“待人工审核”“可借鉴”“注意”等流程性或扩展说明。
3. review_status 默认填 待审核。
4. 不把预标注直接当成最终确认。
```

给 Codex 的固定指令：

```text
请读取 xhs_sample_pool_v1.csv 中 review_status 为空或为 待审核 的新增样本，结合本地封面图和标注规范，完成预标注。不要只按关键词判断。标注完成后保留 review_status=待审核，给我人工审核空间。
```

注意：

```text
Codex 预标注可以读取图片、标题、正文和已有标注经验，准确率高于简单规则脚本。
但它仍然是预标注，不替代人工最终审核。
默认不覆盖 review_status=已确认 的人工标注。
```

标注时不要只看画风像不像蓝汐，要看：

```text
情绪结构能不能迁移
标题方式能不能迁移
角色关系能不能迁移
画面构图能不能迁移
有没有发布风险
```

## 7. 入库前检查

导入 MySQL 前，必须检查这些条件：

```text
1. 新增样本已经进入 xhs_sample_pool_v1.csv
2. images 不为空
3. local_image_path 不为空
4. local_image_path 指向的本地图片存在
5. topic/scene/emotion/hook/reusable_structure/risk_level/keep_status 已填写
6. review_status 已确认，或明确保留为 待审核
7. 没有重复 url/note_id
```

入库前质量检查要覆盖以下问题：

```text
1. 重复样本
   - 检查 id 是否重复
   - 检查 note_id 是否重复
   - 检查 url 去掉 ? 后的主体链接是否重复
   - 当前 validate_sample_pool.py 已覆盖

2. 字段缺失
   - 检查必要字段是否存在
   - 检查 images、local_image_path 是否为空
   - 检查 topic/scene/emotion/hook/reusable_structure/risk_level/keep_status 是否为空
   - 检查 local_image_path 指向的本地图片是否真实存在
   - 当前 validate_sample_pool.py 已覆盖

3. 链接失效
   - 检查 url 是否为空或格式异常
   - 检查 images 链接是否为空或明显不是图片链接
   - 检查本地图片是否已成功下载
   - 当前 validate_sample_pool.py 已覆盖本地图片存在性
   - 原始小红书 url 是否还能在线访问，暂时不作为每次入库必跑项；需要时再单独做抽检，因为频繁访问可能触发平台风控

4. 互动数据异常
   - likes/comments/collects 必须是非负整数
   - 不能出现空值、负数、中文单位未转换的值，例如 1万、3000+
   - 如出现 likes=0 但 comments/collects 极高，或单项数据异常大，需要进入 warnings 人工复核
   - 当前 validate_sample_pool.py 已覆盖整数格式检查
   - 极端值/比例异常目前建议后续增强脚本

5. 采集时间异常
   - scraped_at 应该能解析为时间
   - push_time 应该统一为 YYYY/MM/DD 或可导入 MySQL 的日期格式
   - push_time 不应晚于 scraped_at
   - push_time 不应明显晚于当前日期
   - “昨天”“4天前”“编辑于 浙江”等相对时间和 IP 属地，应在 xhs_data_processing.ipynb 中先清洗
   - 当前流程已在 notebook 中处理 push_time 规范化
   - scraped_at/push_time 的严格日期逻辑建议后续增强 validate_sample_pool.py
```

判断原则：

```text
errors：会破坏入库或导致核心字段不可用的问题，例如重复 id、缺少图片、缺少必填标注、本地图片不存在。
warnings：不一定阻断入库，但需要人工知道的问题，例如待审核样本、历史 notes 缺失、互动数据极端值、时间字段可疑。
```

这一步现在已经固定为脚本：

```text
D:/codex/project-001/Database/pipeline/validate_sample_pool.py
```

运行基础检查：

```powershell
D:\python\python.exe D:\codex\project-001\Database\pipeline\validate_sample_pool.py
```

如果要求所有样本都必须人工确认后才能入库，运行：

```powershell
D:\python\python.exe D:\codex\project-001\Database\pipeline\validate_sample_pool.py --require-confirmed
```

目标结果应类似：

```text
validate_sample_pool completed
rows: 490
errors: 0
warnings: 0
```

如果 `errors` 大于 0，不要导入 MySQL，先修复 CSV。

如果只有 `warnings`，说明存在需要注意的问题，但不一定阻断导入。例如：部分中风险或降权样本缺少 `notes`。

### 7.1 Windows 终端编码注意事项

在 PowerShell 或 VS Code 终端里直接打印 CSV 内容时，如果标题、正文里包含特殊字符、外文字符或 emoji 残留，可能出现：

```text
UnicodeEncodeError: 'gbk' codec can't encode character
```

这是 Windows 终端默认输出编码和数据内容不匹配导致的，不代表 CSV 已损坏。

固定处理方式：

```powershell
$env:PYTHONIOENCODING='utf-8'
```

如果需要在同一条命令里运行 Python，先设置环境变量：

```powershell
$env:PYTHONIOENCODING='utf-8'; D:\python\python.exe your_script.py
```

流程要求：

```text
1. 以后凡是 Python 命令会打印 title、content、tags、notes 等中文或特殊字符字段，都先设置 PYTHONIOENCODING=utf-8。
2. 如果只是读取和写入 CSV，不打印这些字段，通常不受影响。
3. 如果再次遇到编码报错，停止当前流程，不继续执行入库，先修正输出编码或减少终端打印内容。
```

## 8. 导入 MySQL

导入脚本：

```text
D:/codex/project-001/Database/import_xhs_samples.py
```

运行命令：

```powershell
D:\python\python.exe D:\codex\project-001\Database\import_xhs_samples.py --user xhs_user
```

成功输出类似：

```text
Import completed: 490 rows -> xhs_ip_lab.xhs_samples
CSV: D:\codex\project-001\Database\Datapool\data-pool\xhs_sample_pool_v1.csv
```

说明：

- 这个脚本读取的是标准样本池 CSV。
- 它不是直接读取 Easy Scraper 原始 json。
- 它使用 upsert 逻辑，同一个 `id` 已存在时会更新旧记录，不会重复插入。

## 9. 入库后验证

终端验证：

```powershell
mysql -u xhs_user -p -h 127.0.0.1 xhs_ip_lab -e "SELECT COUNT(*) AS sample_count FROM xhs_samples;"
```

SQLTools 验证：

```text
SQLTools
→ local-mysql
→ xhs_ip_lab
→ Tables
→ xhs_samples
→ 点击放大镜查看表数据
```

如果看到：

```text
1-50 of 490
```

说明表里有 490 条数据。

也可以运行：

```sql
SELECT keep_status, COUNT(*) AS count
FROM xhs_samples
GROUP BY keep_status
ORDER BY count DESC;
```

## 10. 文本特征工程 v1.0

文本特征工程的目标是把已经清洗、标注、入库的样本，进一步转成可分析、可排序、可召回的内容特征。

这一层不是替代人工标注，而是在人工标注基础上继续抽取：

```text
痛点
标题模板
标题长度分层
平台关键词
互动综合分
互动等级
```

当前版本：

```text
版本：v1.0
方法：Python 规则 + 词典 + 统计
不调用大模型 API
不做语义推理模型训练
```

### 10.1 输入与输出

输入文件：

```text
D:/codex/project-001/Database/Datapool/data-pool/xhs_sample_pool_v1.csv
```

生成脚本：

```text
D:/codex/project-001/Database/pipeline/feature_pipeline.py
```

输出文件：

```text
D:/codex/project-001/Database/Datapool/features/xhs_text_features_v1.csv
```

MySQL 导入脚本：

```text
D:/codex/project-001/Database/import_xhs_features.py
```

MySQL 特征表：

```text
xhs_ip_lab.xhs_text_features
```

### 10.2 当前特征字段

`xhs_text_features_v1.csv` 当前字段：

```text
sample_id
note_id
url
title
topic
scene
emotion
pain_point
content_structure
title_template
title_length_bucket
hook
platform_keywords
likes
comments
collects
engagement_score
keep_status
risk_level
review_status
push_time
engagement_level
```

字段说明：

```text
sample_id：对应 xhs_samples.id
pain_point：规则推断出的用户痛点，例如孤独陪伴、自我治愈、素材需求
content_structure：来自 reusable_structure
title_template：规则归类出的标题模板
title_length_bucket：标题长度分层
platform_keywords：从 tags/title/content 中抽取的平台关键词
engagement_score：点赞、评论、收藏合成后的互动分
engagement_level：按当前样本池分位数切出的高互动/中互动/低互动
```

### 10.3 v1.0 抽取规则

`pain_point` 使用词典规则推断。

当前痛点词典包括：

```text
孤独陪伴
自我治愈
关系依赖
成长迷茫
低能量疲惫
情绪宣泄
被看见需求
素材需求
节日仪式感
```

`title_template` 使用标题关键词和长度规则归类。

当前标题模板包括：

```text
提问型标题
愿望表达型标题
时间节点型标题
素材领取型标题
关系陪伴型标题
情绪共鸣型标题
自我鼓励型标题
短句氛围型标题
英文短句型标题
叙述型标题
无标题
```

`platform_keywords` 优先从 `tags` 中抽取，再从 `title/content` 中补充关键词。

`engagement_score` 当前公式：

```text
raw_score = likes + comments * 3 + collects * 2
engagement_score = log1p(raw_score)
```

权重含义：

```text
点赞权重 = 1
评论权重 = 3
收藏权重 = 2
```

`engagement_level` 当前按所有样本的 `engagement_score` 分位数切分：

```text
score >= 66% 分位数：高互动
score >= 33% 分位数：中互动
score < 33% 分位数：低互动
```

### 10.4 运行方式

先生成特征 CSV：

```powershell
D:\python\python.exe D:\codex\project-001\Database\pipeline\feature_pipeline.py
```

成功输出类似：

```text
feature_pipeline completed
input_rows: 490
feature_rows: 490
output_csv: D:\codex\project-001\Database\Datapool\features\xhs_text_features_v1.csv
```

确认 CSV 内容无误后，再导入 MySQL：

```powershell
D:\python\python.exe D:\codex\project-001\Database\import_xhs_features.py --user xhs_user
```

成功输出类似：

```text
Import completed: 490 rows -> xhs_ip_lab.xhs_text_features
CSV: D:\codex\project-001\Database\Datapool\features\xhs_text_features_v1.csv
```

说明：

```text
import_xhs_features.py 会自动创建 xhs_text_features 表。
导入逻辑是按 sample_id upsert，重复运行不会重复插入。
xhs_text_features.sample_id 通过外键关联 xhs_samples.id。
如果样本主表中不存在对应 id，导入会失败，避免产生孤立特征数据。
```

### 10.5 导入后验证

验证行数：

```sql
SELECT COUNT(*) AS feature_count
FROM xhs_text_features;
```

验证是否有孤立特征：

```sql
SELECT COUNT(*) AS orphan_features
FROM xhs_text_features f
LEFT JOIN xhs_samples s ON f.sample_id = s.id
WHERE s.id IS NULL;
```

目标结果：

```text
feature_count = 490
orphan_features = 0
```

查看互动等级：

```sql
SELECT engagement_level, COUNT(*) AS count
FROM xhs_text_features
GROUP BY engagement_level
ORDER BY count DESC;
```

查看标题模板：

```sql
SELECT title_template, COUNT(*) AS count
FROM xhs_text_features
GROUP BY title_template
ORDER BY count DESC;
```

查看高互动样本的痛点：

```sql
SELECT pain_point, COUNT(*) AS count
FROM xhs_text_features
WHERE engagement_level = '高互动'
GROUP BY pain_point
ORDER BY count DESC;
```

### 10.6 v1.0 边界

当前 v1.0 是规则版，有这些边界：

```text
1. pain_point 是关键词推断，不等同于深层语义理解。
2. title_template 是规则归类，不保证每条都完全准确。
3. platform_keywords 依赖现有词典，词典需要随着样本迭代扩充。
4. engagement_level 是当前样本池内部的相对分层，不是全平台绝对标准。
5. 当前版本只处理文本和标注字段，不分析图片视觉特征。
```

v1.0 的价值是先让样本具备可统计、可筛选、可 SQL 分析的特征层。后续如果需要更高准确度，再考虑人工修正规则、增加词典或引入本地模型/大模型。

## 11. 基于 MySQL 的后续分析

入库完成后，后续分析优先从 MySQL 读取，而不是继续手翻 CSV。

常用分析 SQL：

### 主题分布

```sql
SELECT topic, COUNT(*) AS count
FROM xhs_samples
WHERE keep_status = '保留'
GROUP BY topic
ORDER BY count DESC;
```

### 情绪分布

```sql
SELECT emotion, COUNT(*) AS count
FROM xhs_samples
WHERE keep_status = '保留'
GROUP BY emotion
ORDER BY count DESC;
```

### 可复用结构分布

```sql
SELECT reusable_structure, COUNT(*) AS count
FROM xhs_samples
WHERE keep_status = '保留'
GROUP BY reusable_structure
ORDER BY count DESC;
```

### 高价值样本

```sql
SELECT id, title, likes, collects, topic, emotion, reusable_structure
FROM xhs_samples
WHERE keep_status = '保留'
ORDER BY likes DESC, collects DESC
LIMIT 30;
```

## 12. 每次新增样本的标准 checklist

每次采集新样本后，按这个顺序执行：

```text
[ ] Easy Scraper 导出与 6.json 字段结构一致的 json
[ ] 原始文件放入 data-collection
[ ] 运行 append_raw_to_pool.py，把原始文件追加到 xhs_sample_pool_v1.csv
[ ] 先 dry-run 确认新增行数、去重数量、无效数量和 id 范围
[ ] 运行 xhs_data_processing.ipynb
[ ] 运行 download_images.py 下载新增封面并回填 local_image_path
[ ] 让 Codex 按本流程文档和标注规范完成新增样本预标注
[ ] 人工按标注规范复核 topic/scene/emotion/hook/reusable_structure/risk_level/keep_status/notes
[ ] 人工审核后设置 review_status
[ ] 运行 validate_sample_pool.py 做入库前质量检查
[ ] 运行 import_xhs_samples.py 导入 MySQL
[ ] 运行 feature_pipeline.py 生成 xhs_text_features_v1.csv
[ ] 审核特征 CSV，无误后运行 import_xhs_features.py 导入 xhs_text_features
[ ] 用 SQLTools 或终端验证数据库行数
```

## 13. 当前已固定的脚本/文件

当前已经固定的脚本/文件：

```text
数据清洗：pipeline/xhs_data_processing.ipynb
原始 json 追加到样本池：pipeline/append_raw_to_pool.py
图片下载与 local_image_path 回填：pipeline/download_images.py
入库前完整质量检查：pipeline/validate_sample_pool.py
MySQL 导入：import_xhs_samples.py
文本特征工程：pipeline/feature_pipeline.py
文本特征导入 MySQL：import_xhs_features.py
数据库初始化：init_mysql.sql
用户授权：User.sql
```

至此，采集到落库的主要工程流程已经固定。预标注环节不使用规则脚本，改为 Codex 执行。

仍然不能完全自动化的是人工审核本身。原因是封面图风格、蓝汐气质匹配度、内容风险和是否值得长期参考，都需要人工最终判断。

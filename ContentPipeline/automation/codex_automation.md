# 蓝汐 Codex 自动化

## 目标

每天根据 `ContentPipeline/publish_calendar_v1.csv` 生成一条蓝汐小红书内容包，并使用 Codex 内置 `image_gen` 生成配图。自动化只生成草稿和图片，不自动发布。

## 工作路径

```text
D:\codex\project-001
└─ ContentPipeline
   ├─ publish_calendar_v1.csv
   ├─ topic_candidates_v1.csv
   ├─ automation
   │  ├─ codex_automation.md
   │  └─ generate_daily_package.py
   └─ generated
      ├─ daily_packages
      ├─ images
      └─ pending_publish.md
```

## 自动化步骤

1. 在项目根目录运行：

```powershell
python ContentPipeline/automation/generate_daily_package.py --update-calendar
```

2. 读取命令输出里的 `package_path`。

3. 打开当天内容包，精修：

- 标题候选：保留 5 个，改到自然、简短、像小红书。
- 正文草稿：保留 A/B/C 三版，避免鸡汤、营销腔和过度承诺。
- Tags：保留 8-12 个，避免无关热词。
- 生图提示词：严格锁定蓝汐 Q 版身份。

4. 使用内容包里的 `生图提示词` 调用 Codex 内置 `image_gen`，并使用 `imagegen` skill。

5. 将生成图片复制到：

```text
ContentPipeline/generated/images/
```

命名格式：

```text
<day>_<topic_id>_<slug>_v1.png
```

6. 回写当天内容包的 `图片产物` 区域：

```text
- 图片路径：ContentPipeline/generated/images/...
- 生成方式：Codex 内置 image_gen
```

7. 做四项发布前检查，并在内容包表格中填写初步结论：

- 人设一致性
- 表达自然度
- 合规风险
- 重复度

8. 更新待人工发布清单：

```text
ContentPipeline/generated/pending_publish.md
```

追加当天条目，包含内容包路径、图片路径、发布前检查结论和状态。

9. 如果当前运行来自每日 Codex 自动化，按 GitHub 审核流处理：

- 从 `main` 创建当天分支，格式：`content/lanxi-<day小写>`，例如 `content/lanxi-d5`。
- 只提交当天自动化产物和必要状态文件，例如：
  - `ContentPipeline/publish_calendar_v1.csv`
  - `ContentPipeline/generated/pending_publish.md`
  - `ContentPipeline/generated/daily_packages/D*.md`
  - `ContentPipeline/generated/images/D*.png`
- commit message 使用：`content: add LanXi <day> daily package`。
- push 分支并创建 PR，目标分支为 `main`。优先使用 GitHub connector 创建 PR；如果本地安装并登录了 GitHub CLI，也可以用 `gh pr create`。
- 如果 connector 和 `gh` 都不可用，至少 push 分支，并在结果里说明需要人工从该分支创建 PR。
- PR 是人工审核发布前的检查口；不要自动合并。

10. 停止，等待人工确认发布。

## 重要边界

- 不自动发布小红书。
- 不自动合并每日内容 PR。
- 不改动 `LanXi` 文件夹内角色设定和参考图。
- 不生成包含文字的图片，除非发布日历明确要求。
- 不使用未授权 IP、品牌 Logo、真人肖像或粉丝隐私信息。

## 为什么由 Codex 生图

`generate_daily_package.py` 是普通 Python 脚本，只负责读取日历、生成内容包和更新状态。Codex 内置 `image_gen` 不是本地 Python 包，所以真正生图必须由 Codex 自动化任务执行。

## 完成标准

每次自动化完成时，应至少产出：

- 1 个 Markdown 内容包
- 1 张项目内图片文件
- 内容包中已写入图片路径
- 内容包中四项检查已有初步结论
- `pending_publish.md` 中新增一条待人工发布记录
- 每日自动化运行时，生成 `content/lanxi-<day>` 分支并打开 PR

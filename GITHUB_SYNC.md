# GitHub 同步流程

本仓库用于同步蓝汐内容生产流程、原创资产、每日生成结果和必要的策略文档。不要把原始采集数据、平台链接 token、本地数据库密码、第三方 IP 截图直接推到 GitHub。

## 入库范围

建议入库：

- `ContentPipeline/` 下的发布日历、候选选题、自动化脚本、每日生成 Markdown、待发布清单和蓝汐生成图。
- `LanXi/` 下的蓝汐原创角色资产和角色档案。
- `case-analysis/` 下的分析报告 Markdown。
- `todolist.html` 等项目管理材料。

默认忽略：

- `Database/` 全目录。数据库脚本、SQL、原始采集、样本池、特征 CSV、下载图和本地密码文件都只保留在本机。
- `*.sql`。所有 SQL 文件默认不入库。
- `case-analysis/参考IP/` 下的第三方截图。
- `.vscode/`、缓存、临时目录和环境变量文件。

## 首次 GitHub 化

在项目根目录执行：

```powershell
git init
git status --short
git add .
git status --short
git commit -m "chore: initialize LanXi content pipeline"
git branch -M main
git remote add origin <你的 GitHub 仓库地址>
git push -u origin main
```

如果 GitHub 远程仓库已有内容，先不要直接 push，改用：

```powershell
git remote add origin <你的 GitHub 仓库地址>
git fetch origin
git status --short --branch
```

确认不会覆盖远程历史后再合并或新建分支。

## 每日本地自动化后同步

本地 Codex 自动化每天生成内容后，先检查：

```powershell
git status --short
python -m py_compile ContentPipeline/automation/generate_daily_package.py
```

确认只包含当天应有变更，例如：

- `ContentPipeline/publish_calendar_v1.csv`
- `ContentPipeline/generated/pending_publish.md`
- `ContentPipeline/generated/daily_packages/D*.md`
- `ContentPipeline/generated/images/D*.png`

直接提交到主分支：

```powershell
git add ContentPipeline
git commit -m "content: add LanXi D5 daily package"
git push
```

如果想走 PR：

```powershell
git switch -c content/lanxi-d5
git add ContentPipeline
git commit -m "content: add LanXi D5 daily package"
git push -u origin content/lanxi-d5
```

然后创建 PR，审核 Markdown、图片和 `pending_publish.md` 后合并。Codex 自动化优先使用 GitHub connector 创建 PR；如果本地安装并登录了 GitHub CLI，也可以用：

```powershell
gh pr create --base main --head content/lanxi-d5 --title "content: add LanXi D5 daily package" --body "Daily LanXi D5 package for human review."
```

如果 connector 和 `gh` 都不可用，至少要把分支 push 到 GitHub，并在运行结果里给出可手动创建 PR 的分支名。

## 新账号数据更新后同步

新采集或新账号数据先在本地完成清洗、标注、入库和策略更新。数据库相关材料不提交到 GitHub；只同步会影响内容生产的非数据库产物，例如 `ContentPipeline/` 的日历、候选选题、生成包、图片和待发布清单。

建议检查：

```powershell
git status --short
git diff --stat
rg -n -i "xsec[_-]?token|password|secret|api[_-]?key|bearer|authorization|cookie" . --glob "!GITHUB_SYNC.md"
```

如果确实需要共享样本特征，先生成脱敏摘要，并放在非 `Database/` 路径下单独评估是否入库。

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DIR = PROJECT_ROOT / "ContentPipeline"
DEFAULT_CALENDAR = PIPELINE_DIR / "publish_calendar_v1.csv"
DEFAULT_TOPICS = PIPELINE_DIR / "topic_candidates_v1.csv"
DEFAULT_OUT_DIR = PIPELINE_DIR / "generated" / "daily_packages"


CALENDAR_STATUS_PENDING = "待生成"
CALENDAR_STATUS_DRAFTED = "已生成草稿"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def day_number(day: str) -> int:
    match = re.search(r"\d+", day or "")
    if not match:
        return 9999
    return int(match.group(0))


def slug_text(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]", "_", value.strip())
    value = re.sub(r"\s+", "_", value)
    return value[:40] or "untitled"


def choose_calendar_row(rows: list[dict[str, str]], day: str | None) -> dict[str, str]:
    if day:
        normalized = day.upper()
        for row in rows:
            if row.get("day", "").upper() == normalized:
                return row
        raise ValueError(f"Calendar day not found: {day}")

    pending = [
        row
        for row in rows
        if (row.get("生产状态") or "").strip() in {"", CALENDAR_STATUS_PENDING}
    ]
    if not pending:
        raise ValueError("No pending calendar rows found.")
    return sorted(pending, key=lambda row: day_number(row.get("day", "")))[0]


def index_topics(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("topic_id", ""): row for row in rows if row.get("topic_id")}


def safe_get(row: dict[str, str] | None, key: str) -> str:
    if not row:
        return ""
    return row.get(key, "")


def build_title_candidates(calendar: dict[str, str], topic: dict[str, str] | None) -> list[str]:
    base = calendar.get("标题方向") or calendar.get("发布主题") or safe_get(topic, "选题方向")
    hook = calendar.get("互动钩子") or safe_get(topic, "互动钩子")
    column = calendar.get("栏目", "")
    titles = [
        base,
        safe_get(topic, "选题方向") or base,
        calendar.get("故事线节点", ""),
        f"{column}｜{base}" if column else base,
        hook.replace("？", "").replace("?", "") if hook else base,
    ]
    deduped: list[str] = []
    for title in titles:
        title = title.strip(" 。")
        if title and title not in deduped:
            deduped.append(title)
    return deduped[:5]


def build_tags(calendar: dict[str, str], topic: dict[str, str] | None) -> list[str]:
    raw = [
        "蓝汐",
        "原创IP",
        "原创插画",
        "治愈系插画",
        "可爱头像",
        calendar.get("栏目", ""),
        calendar.get("内容形式", ""),
        safe_get(topic, "场景"),
        safe_get(topic, "痛点/情绪"),
    ]
    tags: list[str] = []
    for item in raw:
        for part in re.split(r"[;；/、\s]+", item or ""):
            clean = part.strip("# ，,")
            if clean and clean not in tags:
                tags.append(clean)
    return tags[:12]


def build_image_prompt(calendar: dict[str, str], topic: dict[str, str] | None) -> str:
    visual = calendar.get("画面方向") or safe_get(topic, "画面方向")
    form = calendar.get("内容形式") or safe_get(topic, "故事线推荐内容形式")
    return f"""小红书 3:4 竖版发布图，无文字，无水印。

请同时参考两张角色图：LanXi/蓝汐-Q版.png 与 LanXi/蓝汐-Q版-角色参照图.png。这两张图共同定义蓝汐 Q 版身份；若文字与参考图冲突，以参考图为准。

内容形式：{form}
画面方向：{visual}

蓝汐身份锁定：蓝汐是唯一角色和视觉焦点。保持 Q 版大头小身比例、圆润幼态脸、蓝色大眼睛、蓝色眉毛和蓝色睫毛、暖白肤色、蜜桃粉腮红、小而克制的嘴、黑色至深炭黑长发、侧分刘海、纯白无袖连衣裙和默认光脚。蓝色挑染只允许出现在左右发梢末端，不能出现在刘海、头顶、上半段或中段头发。不得添加发卡、帽子、首饰、鞋袜、外套或其他配饰。

风格：柔和 Q 版手绘插画，水彩/粉蜡笔质感，纸面纹理，低饱和，低对比，干净留白。张力来自空间层次、轻微动作、镜头和叙事瞬间，不来自夸张表情或高能量动作。

禁用：文字、水印、Logo、其他角色、品牌元素、复杂花纹、未说明道具、动物耳朵、翅膀、角、尾巴、武器、霓虹、高饱和色块、强烈戏剧光、爆炸、速度线、战斗感、惊恐、尖叫、愤怒、性感化、写实摄影、3D、赛璐璐动漫、矢量、油画、厚涂、高对比商业插画。
""".strip()


def build_markdown(calendar: dict[str, str], topic: dict[str, str] | None) -> str:
    title_candidates = build_title_candidates(calendar, topic)
    tags = build_tags(calendar, topic)
    image_prompt = build_image_prompt(calendar, topic)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    topic_block = ""
    if topic:
        topic_block = f"""
## 候选选题依据

- topic_id：{topic.get("topic_id", "")}
- 选题方向：{topic.get("选题方向", "")}
- 标题模板：{topic.get("标题模板", "")}
- 内容结构：{topic.get("内容结构", "")}
- 痛点/情绪：{topic.get("痛点/情绪", "")}
- 参考样本_id：{topic.get("参考样本_id", "")}
- 参考样本依据：{topic.get("参考样本依据", "")}
- 蓝汐适配理由：{topic.get("蓝汐适配理由", "")}
- 合规风险：{topic.get("合规风险", "")}
- 重复度关键词：{topic.get("重复度关键词", "")}
""".strip()
    else:
        topic_block = "## 候选选题依据\n\n本日历行没有绑定候选选题，按故事线原生内容生成。"

    title_lines = "\n".join(f"{i + 1}. {title}" for i, title in enumerate(title_candidates))
    tag_line = " ".join(f"#{tag}" for tag in tags)

    return f"""# {calendar.get("day", "")} {calendar.get("发布主题", "")}

生成时间：{now}

## 发布日历信息

- calendar_id：{calendar.get("calendar_id", "")}
- day：{calendar.get("day", "")}
- 阶段：{calendar.get("阶段", "")}
- 故事线节点：{calendar.get("故事线节点", "")}
- 栏目：{calendar.get("栏目", "")}
- 主topic_id：{calendar.get("主topic_id", "")}
- 备选topic_id：{calendar.get("备选topic_id", "")}
- 内容形式：{calendar.get("内容形式", "")}
- 来源类型：{calendar.get("来源类型", "")}

{topic_block}

## 标题候选

{title_lines}

## 正文草稿

### 版本 A：自然小红书口吻

{calendar.get("标题方向", "")}

{calendar.get("互动钩子", "")}

### 版本 B：更短更留白

{calendar.get("发布主题", "")}

{calendar.get("互动钩子", "")}

### 版本 C：互动更强

{calendar.get("发布主题", "")}

想听听你会怎么接住这一小段。
{calendar.get("互动钩子", "")}

## Tags

{tag_line}

## 生图提示词

```text
{image_prompt}
```

## 发布前四项检查

| 检查项 | 当前结论 | 待改问题 |
|---|---|---|
| 人设一致性 | 待人工复核 |  |
| 表达自然度 | 待人工复核 |  |
| 合规风险 | 待人工复核 |  |
| 重复度 | 待人工复核 |  |

## 图片产物

- 图片路径：
- 生成方式：Codex 内置 image_gen

## 人工确认区

- 是否可发布：
- 最终标题：
- 最终正文：
- 最终 tags：
- 发布链接：
- 复盘备注：
"""


def update_calendar_status(path: Path, rows: list[dict[str, str]], target_id: str, package_path: Path) -> None:
    fieldnames = list(rows[0].keys())
    optional_fields = ["内容包路径", "生成时间"]
    for field in optional_fields:
        if field not in fieldnames:
            fieldnames.append(field)
            for row in rows:
                row[field] = ""

    for row in rows:
        if row.get("calendar_id") == target_id:
            row["生产状态"] = CALENDAR_STATUS_DRAFTED
            row["内容包路径"] = str(package_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            row["生成时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    write_csv(path, rows, fieldnames)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a daily Lanxi content package from the publish calendar.")
    parser.add_argument("--day", help="Calendar day to generate, such as D4. Defaults to the first pending row.")
    parser.add_argument("--calendar", default=str(DEFAULT_CALENDAR), help="Path to publish_calendar_v1.csv.")
    parser.add_argument("--topics", default=str(DEFAULT_TOPICS), help="Path to topic_candidates_v1.csv.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory for Markdown packages.")
    parser.add_argument("--update-calendar", action="store_true", help="Mark the selected calendar row as drafted.")
    args = parser.parse_args()

    calendar_path = Path(args.calendar)
    topics_path = Path(args.topics)
    out_dir = Path(args.out_dir)

    calendar_rows = read_csv(calendar_path)
    topic_rows = read_csv(topics_path)
    topic_by_id = index_topics(topic_rows)

    row = choose_calendar_row(calendar_rows, args.day)
    topic_id = row.get("主topic_id", "")
    topic = topic_by_id.get(topic_id) if topic_id else None

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{row.get('day', 'DXX')}_{row.get('calendar_id', 'CAL')}_{slug_text(row.get('发布主题', 'untitled'))}.md"
    output_path = out_dir / filename
    output_path.write_text(build_markdown(row, topic), encoding="utf-8")

    if args.update_calendar:
        update_calendar_status(calendar_path, calendar_rows, row.get("calendar_id", ""), output_path)

    result = {
        "calendar_id": row.get("calendar_id", ""),
        "day": row.get("day", ""),
        "topic_id": topic_id,
        "package_path": str(output_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "image_prompt_source": "生图提示词 section in package",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

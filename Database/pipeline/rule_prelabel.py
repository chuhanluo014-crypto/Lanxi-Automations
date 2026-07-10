from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POOL_PATH = PROJECT_ROOT / "Database" / "Datapool" / "data-pool" / "xhs_sample_pool_v1.csv"

ANNOTATION_COLUMNS = [
    "topic",
    "scene",
    "emotion",
    "hook",
    "reusable_structure",
    "risk_level",
    "keep_status",
    "notes",
    "review_status",
]

REQUIRED_COLUMNS = [
    "topic",
    "scene",
    "emotion",
    "hook",
    "reusable_structure",
    "risk_level",
    "keep_status",
]


def contains(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text.lower() for keyword in keywords)


def compact_text(row: dict[str, str]) -> str:
    return " ".join(str(row.get(column, "") or "") for column in ["title", "content", "tags", "author_name"])


def predict_topic(text: str) -> str:
    if contains(text, ["头像", "壁纸", "apple id", "锁屏", "主页", "三件套"]):
        return "头像/壁纸分享"
    if contains(text, ["表情包", "微信", "聊天", "回复", "贴纸"]):
        return "表情包/社交素材"
    if contains(text, ["生日", "新年", "春节", "圣诞", "毕业", "高考", "考试", "春天", "夏天", "秋天", "冬天", "520"]):
        return "节日/节点内容"
    if contains(text, ["诞生", "初次见面", "认识一下", "角色介绍", "设定", "档案", "名字"]):
        return "IP诞生/角色介绍"
    if contains(text, ["过程", "教程", "画法", "草稿", "改版", "制作", "排版"]):
        return "角色设定/创作过程"
    if contains(text, ["联名", "周边", "礼盒", "casetify", "华为", "medm", "手表", "商品"]):
        return "潮玩/周边"
    if contains(text, ["展览", "画展", "快闪", "打卡", "现场"]):
        return "潮玩/周边"
    if contains(text, ["二创", "疯狂动物城", "游戏", "热点", "梗"]):
        return "梗图/热点二创"
    if contains(text, ["征集", "评论区", "点单", "to签", "留言"]):
        return "粉丝共创"
    return "日常陪伴"


def predict_scene(text: str, topic: str) -> str:
    if topic == "头像/壁纸分享":
        return "社交主页/头像;手机/桌面壁纸"
    if topic == "表情包/社交素材":
        return "聊天互动"
    if topic == "节日/节点内容":
        return "节日/纪念日"
    if topic == "粉丝共创":
        return "聊天互动"
    if contains(text, ["朋友", "闺蜜", "小狗", "小猫", "兔子", "小马", "关系", "陪你", "抱抱"]):
        return "朋友/关系互动"
    if contains(text, ["睡", "夜晚", "月亮", "独处", "安静", "发呆", "孤独", "一个人"]):
        return "睡前/独处"
    if contains(text, ["上班", "学习", "考试", "工作", "打工"]):
        return "学习/工作"
    return "日常娱乐"


def predict_emotion(text: str) -> str:
    if contains(text, ["孤独", "难过", "委屈", "哭", "低落", "躲起来", "避难", "沉默", "离开"]):
        return "低落/孤独;治愈"
    if contains(text, ["朋友", "陪", "抱抱", "守护", "亲爱", "想你", "兔子", "小狗", "小猫"]):
        return "亲近/友情;治愈"
    if contains(text, ["加油", "好运", "顺利", "鼓励", "勇敢", "进步", "快乐"]):
        return "鼓励;治愈"
    if contains(text, ["crush", "心动", "浪漫", "喜欢", "爱", "礼物"]):
        return "浪漫;治愈"
    if contains(text, ["搞怪", "无敌", "略略", "大王", "笨蛋", "哈哈", "抽象"]):
        return "可爱;搞怪"
    if contains(text, ["安静", "月亮", "发呆", "轻轻", "淡淡", "松弛"]):
        return "安静/松弛;治愈"
    if contains(text, ["好奇", "为什么", "如何", "你好", "看见"]):
        return "可爱;好奇"
    return "治愈;可爱"


def predict_hook(text: str, topic: str) -> str:
    if topic == "IP诞生/角色介绍":
        return "角色初见"
    if topic == "头像/壁纸分享":
        return "头像可用;壁纸/素材可用"
    if topic == "表情包/社交素材":
        return "壁纸/素材可用"
    if topic == "粉丝共创" or contains(text, ["评论", "留言", "征集", "点单"]):
        return "评论区征集"
    if topic == "节日/节点内容":
        return "节日/热点;情绪共鸣"
    if topic == "梗图/热点二创":
        return "节日/热点;视觉反差"
    if contains(text, ["头像", "壁纸", "保存", "领取"]):
        return "头像可用;壁纸/素材可用"
    if contains(text, ["大", "无敌", "奇怪", "宇宙", "星星", "夸张"]):
        return "视觉反差;情绪共鸣"
    return "情绪共鸣"


def predict_structure(text: str, topic: str, hook: str) -> str:
    if topic == "IP诞生/角色介绍":
        return "角色诞生+互动邀请"
    if topic == "头像/壁纸分享":
        return "头像素材+领取提示"
    if topic == "表情包/社交素材":
        return "表情包素材+领取提示"
    if topic == "粉丝共创":
        return "粉丝征集+创作回馈"
    if topic == "节日/节点内容":
        return "节日祝福+角色回应"
    if topic == "角色设定/创作过程":
        return "制作过程+结果展示"
    if topic == "梗图/热点二创":
        return "热点借势+角色反应"
    if contains(text, ["朋友", "小狗", "小猫", "兔子", "小马", "守护", "抱抱"]):
        return "角色+朋友/动物+陪伴短句"
    if contains(text, ["无敌", "跑", "飞", "跳", "大王", "忍者", "滑板"]):
        return "夸张动作+短标题+角色状态"
    if "视觉反差" in hook:
        return "夸张动作+短标题+角色状态"
    return "日常情绪+陪伴短句"


def predict_risk_and_keep(text: str, topic: str) -> tuple[str, str, str]:
    if contains(text, ["抄袭", "二改", "搬运", "盗图", "禁止"]):
        return "中", "降权", "含版权/搬运相关提示，发布前需避开原表达。"
    if topic in {"潮玩/周边", "梗图/热点二创"}:
        return "中", "降权", "偏商业、周边或热点二创，结构可参考但不宜作为蓝汐主样本。"
    if contains(text, ["死亡", "血", "攻击", "仇恨", "屎", "上帝"]):
        return "中", "降权", "含争议或边缘表达，需人工复核后再决定是否采用。"
    return "低", "保留", "规则预标为低风险可参考样本，需人工复核封面和语境。"


def make_prediction(row: dict[str, str]) -> dict[str, str]:
    text = compact_text(row)
    topic = predict_topic(text)
    hook = predict_hook(text, topic)
    risk, keep, reason = predict_risk_and_keep(text, topic)
    return {
        "topic": topic,
        "scene": predict_scene(text, topic),
        "emotion": predict_emotion(text),
        "hook": hook,
        "reusable_structure": predict_structure(text, topic, hook),
        "risk_level": risk,
        "keep_status": keep,
        "notes": f"规则预标；依据：{reason}；请人工结合封面图确认。",
        "review_status": "待审核",
    }


def read_pool(pool_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not pool_path.exists():
        raise FileNotFoundError(f"Sample pool not found: {pool_path}")
    with pool_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_pool(pool_path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with pool_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_id_filter(value: str) -> set[str]:
    if not value:
        return set()
    ids: set[str] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            if start.strip().isdigit() and end.strip().isdigit():
                ids.update(str(number) for number in range(int(start), int(end) + 1))
        else:
            ids.add(part)
    return ids


def row_has_missing_required(row: dict[str, str]) -> bool:
    return any(not str(row.get(column, "") or "").strip() for column in REQUIRED_COLUMNS)


def should_prelabel(row: dict[str, str], ids: set[str], overwrite: bool, include_confirmed: bool) -> bool:
    if ids and row.get("id", "") not in ids:
        return False
    if not overwrite and not row_has_missing_required(row):
        return False
    if not include_confirmed and str(row.get("review_status", "")).strip() == "已确认":
        return False
    return True


def prelabel_pool(
    pool_path: Path,
    ids: set[str],
    dry_run: bool,
    overwrite: bool,
    include_confirmed: bool,
) -> dict[str, Any]:
    fieldnames, rows = read_pool(pool_path)
    missing_columns = [column for column in ANNOTATION_COLUMNS if column not in fieldnames]
    if missing_columns:
        raise ValueError(f"Sample pool is missing annotation columns: {missing_columns}")

    targets = [row for row in rows if should_prelabel(row, ids, overwrite, include_confirmed)]
    for row in targets:
        prediction = make_prediction(row)
        for column, value in prediction.items():
            if overwrite or not str(row.get(column, "") or "").strip():
                row[column] = value
        if not overwrite:
            row["review_status"] = "待审核"

    if not dry_run and targets:
        write_pool(pool_path, fieldnames, rows)

    return {
        "pool_path": str(pool_path),
        "targets": len(targets),
        "changed": len(targets),
        "dry_run": dry_run,
        "overwrite": overwrite,
        "include_confirmed": include_confirmed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rule-based prelabeling for new XHS samples.")
    parser.add_argument("--pool", default=str(DEFAULT_POOL_PATH), help="Path to xhs_sample_pool_v1.csv.")
    parser.add_argument("--ids", default="", help="Only process selected ids, e.g. 468-520 or 468,469.")
    parser.add_argument("--dry-run", action="store_true", help="Preview target count without writing.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing annotation fields.")
    parser.add_argument("--include-confirmed", action="store_true", help="Allow processing rows with review_status=已确认.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = prelabel_pool(
        pool_path=Path(args.pool).expanduser().resolve(),
        ids=parse_id_filter(args.ids),
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        include_confirmed=args.include_confirmed,
    )
    print("rule_prelabel completed")
    print(f"pool_path: {result['pool_path']}")
    print(f"targets: {result['targets']}")
    print(f"changed: {result['changed']}")
    print(f"overwrite: {result['overwrite']}")
    print(f"include_confirmed: {result['include_confirmed']}")
    print(f"dry_run: {result['dry_run']}")


if __name__ == "__main__":
    main()


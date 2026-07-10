# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_CSV = PROJECT_ROOT / "Database" / "Datapool" / "data-pool" / "xhs_sample_pool_v1.csv"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "Database" / "Datapool" / "features" / "xhs_text_features_v1.csv"


PAIN_POINT_RULES = {
    "孤独陪伴": [
        "孤独",
        "一个人",
        "没人懂",
        "没有人懂",
        "无人理解",
        "陪我",
        "陪伴",
        "想被找到",
        "不开心",
        "难过",
        "眼泪",
        "流泪",
        "哭",
        "抱抱",
        "失落",
        "失眠",
        "晚安",
        "睡不着",
    ],
    "自我治愈": [
        "治愈",
        "自愈",
        "平安",
        "幸福",
        "勇敢",
        "自由",
        "放过自己",
        "没关系",
        "会好的",
        "好起来",
        "快乐",
        "开心",
        "温柔",
        "疗愈",
        "拥抱自己",
        "爱自己",
    ],
    "关系依赖": [
        "朋友",
        "友情",
        "闺蜜",
        "小狗",
        "小猫",
        "小熊",
        "我们",
        "你和我",
        "我和你",
        "永远",
        "依靠",
        "相遇",
        "遇见",
        "在一起",
        "陪你",
        "陪着你",
        "forever",
        "friendship",
    ],
    "成长迷茫": [
        "长大",
        "未来",
        "意义",
        "选择",
        "迷茫",
        "生活",
        "逃离",
        "世界",
        "焦虑",
        "困住",
        "分界线",
        "不知道",
        "为什么",
        "存在",
        "成年人",
        "小时候",
    ],
    "低能量疲惫": [
        "累",
        "疲惫",
        "困",
        "不想动",
        "摆烂",
        "发呆",
        "休息",
        "安静",
        "淡淡的",
        "松弛",
        "低电量",
        "缓一缓",
        "喘口气",
    ],
    "情绪宣泄": [
        "讨厌",
        "委屈",
        "生气",
        "崩溃",
        "遗憾",
        "失望",
        "失约",
        "难受",
        "心事",
        "痛苦",
        "告别",
        "离开",
        "回不去",
    ],
    "被看见需求": [
        "看见我",
        "记得我",
        "被记住",
        "属于我",
        "我的名字",
        "投稿",
        "点单",
        "评论区",
        "许愿",
        "领取",
        "求",
        "想要",
        "可以画",
    ],
    "素材需求": [
        "头像",
        "壁纸",
        "Apple ID",
        "配色",
        "保存",
        "领取",
        "分享",
        "情头",
        "背景图",
        "表情包",
        "朋友圈",
        "锁屏",
        "桌面",
    ],
    "节日仪式感": [
        "生日",
        "圣诞",
        "新年",
        "跨年",
        "毕业",
        "开学",
        "考试",
        "冬天",
        "夏天",
        "秋天",
        "春天",
        "纪念日",
        "晚安",
    ],
}


PLATFORM_KEYWORDS = [
    "头像",
    "壁纸",
    "情头",
    "Apple ID",
    "原创IP",
    "原创ip",
    "插画",
    "治愈",
    "可爱",
    "软萌",
    "萌",
    "小众",
    "分享",
    "保存",
    "领取",
    "评论区",
    "点单",
    "投稿",
    "许愿",
    "名字",
    "表情包",
    "朋友圈",
    "背景图",
    "锁屏",
    "桌面",
    "配色",
    "蓝色",
    "天使",
    "翅膀",
    "小狗",
    "小猫",
    "小熊",
    "兔子",
    "朋友",
    "陪伴",
    "孤独",
    "情绪",
    "低落",
    "不开心",
    "眼泪",
    "晚安",
    "幸福",
    "自由",
    "勇敢",
    "平安",
    "生日",
    "圣诞",
    "新年",
    "冬天",
    "夏天",
    "下雨",
    "雪",
    "海",
    "云",
    "星星",
    "月亮",
    "Bambina",
    "bambina",
    "IP",
]


TITLE_TEMPLATE_RULES = [
    ("提问型标题", ["吗", "？", "?"]),
    ("愿望表达型标题", ["我想", "我只希望", "希望", "想要", "许愿"]),
    ("时间节点型标题", ["今天", "晚安", "生日", "圣诞", "冬", "夏天", "下雨", "雪", "秋", "新年"]),
    ("素材领取型标题", ["头像", "壁纸", "分享", "配色", "Apple ID", "情头", "表情包"]),
    ("关系陪伴型标题", ["朋友", "我们", "你和我", "陪你", "遇见", "永远", "小狗", "小猫", "小熊"]),
    ("情绪共鸣型标题", ["没人", "不开心", "难过", "眼泪", "孤独", "遗憾", "失望", "逃离", "心事"]),
    ("自我鼓励型标题", ["勇敢", "平安", "幸福", "自由", "长大", "存在的意义", "爱自己"]),
]


def safe_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def safe_int(value: Any) -> int:
    if pd.isna(value):
        return 0
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def split_tags(value: Any) -> list[str]:
    text = safe_text(value)
    if not text:
        return []
    tags = []
    for item in re.split(r"[;；,，\s]+", text):
        item = item.strip()
        if item and item not in tags:
            tags.append(item)
    return tags


def joined_text(row: pd.Series, columns: list[str]) -> str:
    return " ".join(safe_text(row.get(column, "")) for column in columns)


def extract_platform_keywords(row: pd.Series, max_keywords: int = 15) -> str:
    text = joined_text(row, ["title", "content", "tags"])
    found: list[str] = []

    for tag in split_tags(row.get("tags")):
        clean_tag = tag.lstrip("#").strip()
        if clean_tag and clean_tag not in found:
            found.append(clean_tag)

    for keyword in PLATFORM_KEYWORDS:
        if keyword in text and keyword not in found:
            found.append(keyword)

    return "; ".join(found[:max_keywords])


def infer_pain_point(row: pd.Series, max_items: int = 2) -> str:
    text = joined_text(row, ["title", "content", "tags", "topic", "scene", "emotion", "hook"])
    matched: list[str] = []

    for pain_point, keywords in PAIN_POINT_RULES.items():
        if any(keyword in text for keyword in keywords):
            matched.append(pain_point)

    if not matched:
        return "无明显痛点"
    return "; ".join(matched[:max_items])


def infer_title_template(title: Any) -> str:
    title_text = safe_text(title)
    if not title_text:
        return "无标题"

    for template, keywords in TITLE_TEMPLATE_RULES:
        if any(keyword in title_text for keyword in keywords):
            return template

    if len(title_text) <= 8:
        return "短句氛围型标题"

    if re.search(r"^[A-Za-z0-9 ,.'!?-]+$", title_text):
        return "英文短句型标题"

    return "叙述型标题"


def infer_title_length_bucket(title: Any) -> str:
    length = len(safe_text(title))
    if length == 0:
        return "无标题"
    if length <= 6:
        return "超短标题"
    if length <= 12:
        return "短标题"
    if length <= 24:
        return "中标题"
    return "长标题"


def calc_engagement_score(row: pd.Series) -> float:
    likes = safe_int(row.get("likes"))
    comments = safe_int(row.get("comments"))
    collects = safe_int(row.get("collects"))
    raw_score = likes + comments * 3 + collects * 2
    return round(math.log1p(max(raw_score, 0)), 4)


def infer_engagement_level(score: float, q33: float, q66: float) -> str:
    if score >= q66:
        return "高互动"
    if score >= q33:
        return "中互动"
    return "低互动"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        score = calc_engagement_score(row)
        rows.append(
            {
                "sample_id": row.get("id", ""),
                "note_id": row.get("note_id", ""),
                "url": row.get("url", ""),
                "title": row.get("title", ""),
                "topic": row.get("topic", ""),
                "scene": row.get("scene", ""),
                "emotion": row.get("emotion", ""),
                "pain_point": infer_pain_point(row),
                "content_structure": row.get("reusable_structure", ""),
                "title_template": infer_title_template(row.get("title")),
                "title_length_bucket": infer_title_length_bucket(row.get("title")),
                "hook": row.get("hook", ""),
                "platform_keywords": extract_platform_keywords(row),
                "likes": safe_int(row.get("likes")),
                "comments": safe_int(row.get("comments")),
                "collects": safe_int(row.get("collects")),
                "engagement_score": score,
                "keep_status": row.get("keep_status", ""),
                "risk_level": row.get("risk_level", ""),
                "review_status": row.get("review_status", ""),
                "push_time": row.get("push_time", ""),
            }
        )

    features = pd.DataFrame(rows)
    if not features.empty:
        q33 = float(features["engagement_score"].quantile(0.33))
        q66 = float(features["engagement_score"].quantile(0.66))
        features["engagement_level"] = features["engagement_score"].apply(
            lambda score: infer_engagement_level(float(score), q33, q66)
        )

    return features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build text feature CSV from xhs_sample_pool_v1.csv.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_CSV), help="Input sample pool CSV path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_CSV), help="Output feature CSV path.")
    parser.add_argument(
        "--include-removed",
        action="store_true",
        help="Include keep_status=剔除 rows if they exist. Default excludes them.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path, encoding="utf-8-sig")
    if not args.include_removed and "keep_status" in df.columns:
        df = df[df["keep_status"].fillna("").astype(str).str.strip() != "剔除"].copy()

    features = build_features(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("feature_pipeline completed")
    print(f"input_rows: {len(df)}")
    print(f"feature_rows: {len(features)}")
    print(f"output_csv: {output_path}")
    if not features.empty:
        print(f"pain_point_top: {features['pain_point'].value_counts().head(8).to_dict()}")
        print(f"title_template_top: {features['title_template'].value_counts().head(8).to_dict()}")
        print(f"engagement_level: {features['engagement_level'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()

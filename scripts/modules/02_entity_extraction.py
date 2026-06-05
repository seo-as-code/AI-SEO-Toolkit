import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import latest_file, load_project_config, save_csv, timestamp  # noqa: E402

ENTITY_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b")


def extract_entities(text: str) -> list[str]:
    found = ENTITY_PATTERN.findall(str(text))
    cleaned = []
    for item in found:
        value = item.strip()
        if len(value) > 3 and value.lower() not in {"home", "menu", "contact"}:
            cleaned.append(value)
    return cleaned


def run(semantic_path: str | None = None) -> dict:
    cfg = load_project_config()
    semantic_file = semantic_path or latest_file(str(ROOT / "reports/ai/01_semantic_map_*.csv"))
    if not semantic_file or not Path(semantic_file).exists():
        raise FileNotFoundError("Run module 01 first to generate semantic map.")

    sdf = pd.read_csv(semantic_file)
    rows = []
    global_counter = Counter()

    for _, row in sdf.iterrows():
        blob = " ".join(
            [
                str(row.get("title", "")),
                str(row.get("primary_h1", "")),
                str(row.get("topic_keywords", "")),
            ]
        )
        entities = extract_entities(blob)
        for ent in entities:
            global_counter[ent] += 1
            rows.append({"url": row.get("url", ""), "entity": ent, "source": "semantic_map"})

    entity_df = pd.DataFrame(rows)
    summary = (
        entity_df.groupby("entity")
        .agg(url_count=("url", "nunique"), mentions=("entity", "count"))
        .reset_index()
        .sort_values(["mentions", "url_count"], ascending=False)
    )

    ts = timestamp()
    out_dir = ROOT / cfg["output"]["reports_dir"]
    detail_path = out_dir / f"02_entities_{ts}.csv"
    summary_path = out_dir / f"02_entities_summary_{ts}.csv"
    save_csv(entity_df, detail_path)
    save_csv(summary.head(200), summary_path)

    print(f"[02] Entities detail: {detail_path}")
    print(f"[02] Entities summary: {summary_path}")
    return {"detail": str(detail_path), "summary": str(summary_path), "rows": len(entity_df)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 02 - Entity extraction")
    parser.add_argument("--semantic", default="", help="Optional semantic map CSV")
    args = parser.parse_args()
    run(semantic_path=args.semantic or None)

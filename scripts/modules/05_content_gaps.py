import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import latest_file, load_yaml, save_csv, timestamp  # noqa: E402


def normalize_text(value: str) -> set[str]:
    tokens = []
    for part in str(value).lower().replace("-", " ").replace("/", " ").split():
        token = "".join(ch for ch in part if ch.isalnum())
        if len(token) > 3:
            tokens.append(token)
    return set(tokens)


def run(gsc_path: str | None = None, semantic_path: str | None = None) -> dict:
    cfg = load_yaml("project.yaml")
    thresholds = cfg.get("thresholds", {})
    min_impressions = int(thresholds.get("min_impressions_for_gap", 100))

    ds = cfg.get("data_sources", {})
    gsc_file = gsc_path or latest_file(str(ROOT / ds.get("gsc_glob", "../data/raw/gsc_*.csv")))
    semantic_file = semantic_path or latest_file(str(ROOT / "reports/ai/01_semantic_map_*.csv"))

    if not gsc_file or not Path(gsc_file).exists():
        raise FileNotFoundError("GSC CSV not found. Export GSC first or pass --gsc.")

    gsc = pd.read_csv(gsc_file)
    gsc["impressions"] = pd.to_numeric(gsc.get("impressions", 0), errors="coerce").fillna(0)
    gsc["clicks"] = pd.to_numeric(gsc.get("clicks", 0), errors="coerce").fillna(0)
    gsc["position"] = pd.to_numeric(gsc.get("position", 0), errors="coerce").fillna(0)

    query_agg = (
        gsc.groupby("query", dropna=False)
        .agg(impressions=("impressions", "sum"), clicks=("clicks", "sum"), avg_position=("position", "mean"))
        .reset_index()
    )
    query_agg = query_agg[query_agg["impressions"] >= min_impressions].sort_values(
        ["impressions", "clicks"], ascending=[False, True]
    )

    covered_terms = set()
    if semantic_file and Path(semantic_file).exists():
        semantic = pd.read_csv(semantic_file)
        for _, row in semantic.iterrows():
            covered_terms.update(normalize_text(row.get("title", "")))
            covered_terms.update(normalize_text(row.get("primary_h1", "")))
            covered_terms.update(normalize_text(row.get("topic_keywords", "")))

    gaps = []
    for _, row in query_agg.iterrows():
        query = str(row["query"])
        q_terms = normalize_text(query)
        overlap = len(q_terms & covered_terms)
        coverage_ratio = overlap / max(len(q_terms), 1)
        if coverage_ratio < 0.35:
            gaps.append(
                {
                    "query": query,
                    "impressions": int(row["impressions"]),
                    "clicks": int(row["clicks"]),
                    "avg_position": round(float(row["avg_position"]), 2),
                    "coverage_ratio": round(coverage_ratio, 2),
                    "gap_type": "missing_topic" if coverage_ratio < 0.15 else "weak_coverage",
                    "recommended_action": "Create new content cluster" if coverage_ratio < 0.15 else "Expand existing page",
                }
            )

    out_df = pd.DataFrame(gaps).head(200)
    ts = timestamp()
    out_path = ROOT / cfg["output"]["reports_dir"] / f"05_content_gaps_{ts}.csv"
    save_csv(out_df, out_path)

    print(f"[05] Content gaps: {out_path}")
    return {"gaps": str(out_path), "rows": len(out_df)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 05 - Content gap detection")
    parser.add_argument("--gsc", default="", help="Optional GSC CSV path")
    parser.add_argument("--semantic", default="", help="Optional semantic map CSV path")
    args = parser.parse_args()
    run(gsc_path=args.gsc or None, semantic_path=args.semantic or None)

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import latest_file, load_yaml, save_csv, timestamp  # noqa: E402


INTENT_RULES = {
    "transactional": [r"\bbuy\b", r"\bbook\b", r"\breserv", r"\bprice\b", r"\bprecio\b", r"\bcompr"],
    "commercial": [r"\bbest\b", r"\btop\b", r"\bvs\b", r"\bcompare\b", r"\bservicio", r"\bagencia"],
    "navigational": [r"\blogin\b", r"\bcontact\b", r"\bcontacto\b", r"\babout\b", r"\bquienes"],
    "local": [r"\bibiza\b", r"\bnear me\b", r"\bcerca\b", r"\blocal\b"],
    "informational": [r"\bwhat\b", r"\bhow\b", r"\bguide\b", r"\bguia\b", r"\bcomo\b", r"\bque es\b"],
}


def classify_intent(text: str) -> str:
    value = text.lower()
    scores = {}
    for intent, patterns in INTENT_RULES.items():
        score = sum(1 for p in patterns if re.search(p, value))
        if score:
            scores[intent] = score
    if not scores:
        return "mixed"
    return max(scores, key=scores.get)


def run(gsc_path: str | None = None) -> dict:
    cfg = load_yaml("project.yaml")
    ds = cfg.get("data_sources", {})
    gsc_file = gsc_path or latest_file(str(ROOT / ds.get("gsc_glob", "../data/raw/gsc_*.csv")))

    rows = []
    if gsc_file and Path(gsc_file).exists():
        df = pd.read_csv(gsc_file)
        for _, row in df.iterrows():
            query = str(row.get("query", ""))
            page = str(row.get("page", ""))
            label = classify_intent(f"{query} {page}")
            rows.append(
                {
                    "source": "gsc",
                    "query": query,
                    "page": page,
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "position": row.get("position", 0),
                    "intent": label,
                }
            )
    else:
        # Fallback: classify URLs from semantic map if available
        semantic = latest_file(str(ROOT / "reports/ai/01_semantic_map_*.csv"))
        if semantic:
            sdf = pd.read_csv(semantic)
            for _, row in sdf.iterrows():
                label = classify_intent(f"{row.get('title', '')} {row.get('primary_h1', '')}")
                rows.append(
                    {
                        "source": "semantic_map",
                        "query": "",
                        "page": row.get("url", ""),
                        "clicks": 0,
                        "impressions": 0,
                        "position": 0,
                        "intent": label,
                    }
                )

    if not rows:
        raise FileNotFoundError("No GSC CSV and no semantic map found for intent classification.")

    out_df = pd.DataFrame(rows)
    ts = timestamp()
    out_path = ROOT / cfg["output"]["reports_dir"] / f"03_intent_matrix_{ts}.csv"
    save_csv(out_df, out_path)

    summary = out_df.groupby("intent").size().reset_index(name="count").sort_values("count", ascending=False)
    summary_path = ROOT / cfg["output"]["reports_dir"] / f"03_intent_summary_{ts}.csv"
    save_csv(summary, summary_path)

    print(f"[03] Intent matrix: {out_path}")
    print(f"[03] Intent summary: {summary_path}")
    return {"matrix": str(out_path), "summary": str(summary_path), "rows": len(out_df)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 03 - Search intent classifier")
    parser.add_argument("--gsc", default="", help="Optional GSC CSV path")
    args = parser.parse_args()
    run(gsc_path=args.gsc or None)

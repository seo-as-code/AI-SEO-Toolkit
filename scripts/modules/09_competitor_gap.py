import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import fetch_html, latest_file, load_yaml, parse_page, save_csv, timestamp  # noqa: E402


def tokenize(text: str) -> set[str]:
    return {t.lower() for t in str(text).split() if len(t) > 4}


def run(semantic_path: str | None = None) -> dict:
    cfg = load_yaml("project.yaml")
    semantic_file = semantic_path or latest_file(str(ROOT / "reports/ai/01_semantic_map_*.csv"))
    if not semantic_file or not Path(semantic_file).exists():
        raise FileNotFoundError("Run module 01 first.")

    own = pd.read_csv(semantic_file)
    own_terms = set()
    for _, row in own.iterrows():
        own_terms.update(tokenize(row.get("title", "")))
        own_terms.update(tokenize(row.get("topic_keywords", "")))

    rows = []
    for competitor in cfg.get("competitors", []):
        try:
            html = fetch_html(competitor, timeout=15)
            page = parse_page(competitor, html)
            comp_terms = tokenize(page.get("title", "")) | tokenize(page.get("text_sample", ""))
            missing = sorted(list(comp_terms - own_terms))[:30]
            rows.append(
                {
                    "competitor": competitor,
                    "competitor_terms_sample": ", ".join(sorted(list(comp_terms))[:15]),
                    "missing_on_own_site": ", ".join(missing),
                    "opportunity_count": len(missing),
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "competitor": competitor,
                    "competitor_terms_sample": "",
                    "missing_on_own_site": "",
                    "opportunity_count": 0,
                    "error": str(exc),
                }
            )

    out_df = pd.DataFrame(rows)
    ts = timestamp()
    out_path = ROOT / cfg["output"]["reports_dir"] / f"09_competitor_gap_{ts}.csv"
    save_csv(out_df, out_path)
    print(f"[09] Competitor gap: {out_path}")
    return {"csv": str(out_path), "rows": len(out_df)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 09 - Competitor gap analysis")
    parser.add_argument("--semantic", default="")
    args = parser.parse_args()
    run(semantic_path=args.semantic or None)

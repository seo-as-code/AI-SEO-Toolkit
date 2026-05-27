import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import latest_file, load_yaml, save_csv, timestamp  # noqa: E402


def run(sf_path: str | None = None, semantic_path: str | None = None) -> dict:
    cfg = load_yaml("project.yaml")
    ds = cfg.get("data_sources", {})
    sf_file = sf_path or latest_file(str(ROOT / ds.get("sf_csv", "../data/raw/internos_todo.csv")))
    semantic_file = semantic_path or latest_file(str(ROOT / "reports/ai/01_semantic_map_*.csv"))

    issues = []

    if sf_file and Path(sf_file).exists():
        sf = pd.read_csv(sf_file)
        rename_map = {
            "Dirección": "url",
            "Address": "url",
            "Código de respuesta": "status_code",
            "Status Code": "status_code",
            "Indexabilidad": "indexability",
            "Indexability": "indexability",
            "Título 1": "title",
            "Title 1": "title",
            "Meta description 1": "meta_description",
            "Meta Description 1": "meta_description",
            "H1-1": "h1",
        }
        sf = sf.rename(columns=rename_map)
        for _, row in sf.iterrows():
            url = str(row.get("url", ""))
            status = row.get("status_code", 200)
            if pd.notna(status) and int(status) != 200:
                issues.append({"url": url, "issue_type": "status_code", "severity": "high", "detail": f"status={status}"})
            title = str(row.get("title", "")).strip()
            if not title or title.lower() == "nan":
                issues.append({"url": url, "issue_type": "missing_title", "severity": "medium", "detail": "empty title"})
            meta = str(row.get("meta_description", "")).strip()
            if not meta or meta.lower() == "nan":
                issues.append({"url": url, "issue_type": "missing_meta", "severity": "medium", "detail": "empty meta"})
            h1 = str(row.get("h1", "")).strip()
            if not h1 or h1.lower() == "nan":
                issues.append({"url": url, "issue_type": "missing_h1", "severity": "medium", "detail": "empty h1"})

    if semantic_file and Path(semantic_file).exists():
        sdf = pd.read_csv(semantic_file)
        for _, row in sdf.iterrows():
            if int(row.get("word_count", 0)) < 250:
                issues.append(
                    {
                        "url": row.get("url", ""),
                        "issue_type": "thin_content",
                        "severity": "medium",
                        "detail": f"word_count={row.get('word_count', 0)}",
                    }
                )

    if not issues:
        raise FileNotFoundError("No technical inputs found. Provide SF CSV or run module 01.")

    out_df = pd.DataFrame(issues).drop_duplicates()
    ts = timestamp()
    out_path = ROOT / cfg["output"]["reports_dir"] / f"07_technical_audit_{ts}.csv"
    save_csv(out_df, out_path)
    print(f"[07] Technical audit: {out_path}")
    return {"csv": str(out_path), "rows": len(out_df)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 07 - Technical SEO audit")
    parser.add_argument("--sf", default="")
    parser.add_argument("--semantic", default="")
    args = parser.parse_args()
    run(sf_path=args.sf or None, semantic_path=args.semantic or None)

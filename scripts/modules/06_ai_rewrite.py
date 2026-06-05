import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import latest_file, load_project_config, save_md, timestamp  # noqa: E402


def run(gaps_path: str | None = None, semantic_path: str | None = None) -> dict:
    cfg = load_project_config()
    gaps_file = gaps_path or latest_file(str(ROOT / "reports/ai/05_content_gaps_*.csv"))
    semantic_file = semantic_path or latest_file(str(ROOT / "reports/ai/01_semantic_map_*.csv"))

    suggestions = []
    if gaps_file and Path(gaps_file).exists():
        gdf = pd.read_csv(gaps_file).head(15)
        for _, row in gdf.iterrows():
            query = str(row.get("query", "")).strip()
            suggestions.append(
                {
                    "target_query": query,
                    "title_suggestion": f"{query.title()} | {cfg['project']['name']}",
                    "meta_suggestion": f"Descubre {query} con {cfg['project']['name']}. Informacion clara, enfoque local y propuesta de valor.",
                    "h1_suggestion": query.title(),
                    "cta_suggestion": "Solicitar informacion",
                }
            )

    if semantic_file and Path(semantic_file).exists() and len(suggestions) < 5:
        sdf = pd.read_csv(semantic_file).head(10)
        for _, row in sdf.iterrows():
            title = str(row.get("title", "")).strip()
            if not title:
                continue
            suggestions.append(
                {
                    "target_query": title,
                    "title_suggestion": f"{title} | Optimizado",
                    "meta_suggestion": f"Mejora visibilidad para: {title}.",
                    "h1_suggestion": title,
                    "cta_suggestion": "Contactar",
                }
            )

    if not suggestions:
        raise FileNotFoundError("No input found. Run modules 01 and 05 first.")

    ts = timestamp()
    md_path = ROOT / cfg["output"]["reports_dir"] / f"06_ai_rewrite_{ts}.md"
    lines = ["# AI Rewrite Suggestions", ""]
    for item in suggestions:
        lines.extend(
            [
                f"## Query/Page: {item['target_query']}",
                f"- Title: {item['title_suggestion']}",
                f"- Meta: {item['meta_suggestion']}",
                f"- H1: {item['h1_suggestion']}",
                f"- CTA: {item['cta_suggestion']}",
                "",
            ]
        )
    save_md("\n".join(lines), md_path)
    print(f"[06] Rewrite suggestions: {md_path}")
    return {"md": str(md_path), "suggestions": len(suggestions)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 06 - AI rewrite suggestions")
    parser.add_argument("--gaps", default="")
    parser.add_argument("--semantic", default="")
    args = parser.parse_args()
    run(gaps_path=args.gaps or None, semantic_path=args.semantic or None)

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import latest_file, load_project_config, save_csv, save_md, timestamp  # noqa: E402


def analyze_style(text: str) -> dict:
    words = str(text).split()
    sentences = [s for s in str(text).split(".") if s.strip()]
    avg_sentence = (sum(len(s.split()) for s in sentences) / max(len(sentences), 1)) if sentences else 0
    lower = str(text).lower()
    formal_markers = sum(lower.count(w) for w in ["servicio", "solucion", "profesional", "experiencia"])
    direct_markers = sum(lower.count(w) for w in ["tu", "te", "ahora", "gratis", "reserva"])
    tone = "formal" if formal_markers >= direct_markers else "direct"
    readability = "easy" if avg_sentence <= 16 else "medium" if avg_sentence <= 24 else "complex"
    return {
        "word_count": len(words),
        "avg_sentence_length": round(avg_sentence, 2),
        "tone": tone,
        "readability": readability,
    }


def run(semantic_path: str | None = None) -> dict:
    cfg = load_project_config()
    semantic_file = semantic_path or latest_file(str(ROOT / "reports/ai/01_semantic_map_*.json"))
    if not semantic_file:
        semantic_file = latest_file(str(ROOT / "reports/ai/01_semantic_map_*.csv"))
    if not semantic_file or not Path(semantic_file).exists():
        raise FileNotFoundError("Run module 01 first.")

    if semantic_file.endswith(".json"):
        import json

        with open(semantic_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        pages = payload.get("topics", [])
        rows = []
        for page in pages:
            text = " ".join(
                [
                    str(page.get("title", "")),
                    str(page.get("primary_h1", "")),
                    str(page.get("topic_keywords", "")),
                ]
            )
            metrics = analyze_style(text)
            rows.append({"url": page.get("url", ""), **metrics})
    else:
        sdf = pd.read_csv(semantic_file)
        rows = []
        for _, row in sdf.iterrows():
            text = " ".join([str(row.get("title", "")), str(row.get("primary_h1", "")), str(row.get("topic_keywords", ""))])
            rows.append({"url": row.get("url", ""), **analyze_style(text)})

    out_df = pd.DataFrame(rows)
    ts = timestamp()
    csv_path = ROOT / cfg["output"]["reports_dir"] / f"04_tone_style_{ts}.csv"
    md_path = ROOT / cfg["output"]["reports_dir"] / f"04_tone_style_{ts}.md"
    save_csv(out_df, csv_path)

    tone_counts = out_df["tone"].value_counts().to_dict() if not out_df.empty else {}
    dom = max(tone_counts, key=tone_counts.get) if tone_counts else "n/d"
    md = [
        "# Análisis de tono y estilo",
        "",
        f"- Páginas analizadas: {len(out_df)}",
        f"- Tono dominante: {dom}",
        "",
        "## Recomendaciones",
        "- Mantener el mismo tono en landings de servicio y páginas clave.",
        "- Acortar frases en páginas con legibilidad compleja.",
    ]
    save_md("\n".join(md) + "\n", md_path)

    print(f"[04] Tone/style CSV: {csv_path}")
    print(f"[04] Tone/style MD: {md_path}")
    return {"csv": str(csv_path), "md": str(md_path), "rows": len(out_df)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 04 - Tone and style analysis")
    parser.add_argument("--semantic", default="")
    args = parser.parse_args()
    run(semantic_path=args.semantic or None)

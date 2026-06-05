import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import fetch_html, load_project_config, parse_page, save_csv, timestamp  # noqa: E402

CTA_KEYWORDS = ["contact", "contacto", "reserva", "book", "quote", "presupuesto", "llama", "whatsapp"]


def run() -> dict:
    cfg = load_project_config()
    origin = cfg["project"]["origin"]
    crawl_cfg = cfg.get("crawl", {})

    html = fetch_html(origin, timeout=int(crawl_cfg.get("timeout_seconds", 15)))
    page = parse_page(origin, html)
    text = page.get("text_sample", "").lower()

    cta_found = [k for k in CTA_KEYWORDS if k in text]
    nav_links = len(page.get("links", []))
    h1_count = len(page.get("h1", []))

    findings = [
        {
            "url": origin,
            "check": "cta_presence",
            "status": "pass" if cta_found else "fail",
            "detail": ", ".join(cta_found) if cta_found else "No CTA keywords detected",
        },
        {
            "url": origin,
            "check": "navigation_depth",
            "status": "pass" if nav_links >= 8 else "warn",
            "detail": f"internal_links={nav_links}",
        },
        {
            "url": origin,
            "check": "h1_structure",
            "status": "pass" if h1_count == 1 else "warn",
            "detail": f"h1_count={h1_count}",
        },
        {
            "url": origin,
            "check": "message_clarity",
            "status": "pass" if len(page.get("title", "")) >= 20 else "warn",
            "detail": f"title_length={len(page.get('title', ''))}",
        },
    ]

    out_df = pd.DataFrame(findings)
    ts = timestamp()
    out_path = ROOT / cfg["output"]["reports_dir"] / f"08_ux_cro_{ts}.csv"
    save_csv(out_df, out_path)
    print(f"[08] UX/CRO audit: {out_path}")
    return {"csv": str(out_path), "rows": len(out_df)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 08 - UX/CRO analysis")
    parser.parse_args()
    run()

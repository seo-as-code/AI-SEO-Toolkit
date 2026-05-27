import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import (  # noqa: E402
    discover_internal_urls,
    fetch_html,
    load_yaml,
    parse_page,
    save_csv,
    save_json,
    timestamp,
)


def build_semantic_topics(pages: list[dict]) -> list[dict]:
    topics = []
    for page in pages:
        tokens = []
        for field in ["title", "meta_description"] + page.get("h1", []) + page.get("h2", []):
            tokens.extend(str(field).lower().split())
        common = [w for w, _ in Counter(tokens).most_common(8) if len(w) > 3]
        topics.append(
            {
                "url": page["url"],
                "title": page["title"],
                "primary_h1": page["h1"][0] if page.get("h1") else "",
                "topic_keywords": ", ".join(common[:5]),
                "word_count": page["word_count"],
            }
        )
    return topics


def run() -> dict:
    cfg = load_yaml("project.yaml")
    origin = cfg["project"]["origin"]
    domain = cfg["project"]["domain"]
    crawl_cfg = cfg.get("crawl", {})

    urls = discover_internal_urls(
        origin=origin,
        domain=domain,
        max_pages=int(crawl_cfg.get("max_pages", 25)),
        timeout=int(crawl_cfg.get("timeout_seconds", 15)),
        user_agent=str(crawl_cfg.get("user_agent", "AI-SEO-Toolkit/1.0")),
    )

    pages = []
    for url in urls:
        try:
            html = fetch_html(url, timeout=int(crawl_cfg.get("timeout_seconds", 15)))
            pages.append(parse_page(url, html))
        except Exception:
            continue

    topics = build_semantic_topics(pages)
    ts = timestamp()
    out_dir = ROOT / cfg["output"]["reports_dir"]
    json_path = out_dir / f"01_semantic_map_{ts}.json"
    csv_path = out_dir / f"01_semantic_map_{ts}.csv"

    payload = {
        "project": cfg["project"]["name"],
        "origin": origin,
        "pages_analyzed": len(pages),
        "topics": topics,
    }
    save_json(payload, json_path)
    save_csv(__import__("pandas").DataFrame(topics), csv_path)

    print(f"[01] Semantic map JSON: {json_path}")
    print(f"[01] Semantic map CSV: {csv_path}")
    return {"json": str(json_path), "csv": str(csv_path), "pages": len(pages)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 01 - Semantic site map")
    parser.parse_args()
    run()

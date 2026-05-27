import glob
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def is_same_domain(url: str, domain: str) -> bool:
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host == domain.lower().replace("www.", "")


def fetch_html(url: str, timeout: int = 15, user_agent: str = "AI-SEO-Toolkit/1.0") -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": user_agent},
    )
    response.raise_for_status()
    return response.text


def parse_page(url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    title = (soup.title.string or "").strip() if soup.title else ""
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = (meta_desc_tag.get("content") or "").strip() if meta_desc_tag else ""
    h1 = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2 = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    text = soup.get_text(" ", strip=True)
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        links.append(href)
    return {
        "url": url,
        "title": title,
        "meta_description": meta_desc,
        "h1": h1,
        "h2": h2,
        "word_count": len(text.split()),
        "links": links,
        "text_sample": text[:2000],
    }


def discover_internal_urls(origin: str, domain: str, max_pages: int, timeout: int, user_agent: str) -> list[str]:
    queue = [origin.rstrip("/") + "/"]
    seen = set()
    collected = []

    while queue and len(collected) < max_pages:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        try:
            html = fetch_html(current, timeout=timeout, user_agent=user_agent)
            page = parse_page(current, html)
            collected.append(current)
            for link in page["links"]:
                if not is_same_domain(link, domain):
                    continue
                clean = link.split("#")[0].rstrip("/")
                if clean and clean not in seen and clean not in queue:
                    queue.append(clean)
        except Exception:
            continue
    return collected


def latest_file(pattern: str) -> str | None:
    matches = glob.glob(pattern)
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def save_json(data: Any, path: Path) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_dir(path.parent)
    df.to_csv(path, index=False, encoding="utf-8")


def save_md(content: str, path: Path) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_openai_client():
    model_cfg = load_yaml("model.yaml")
    api_key = os.getenv(model_cfg.get("api_key_env", "OPENAI_API_KEY"), "")
    if not api_key:
        return None, model_cfg
    try:
        from openai import OpenAI

        return OpenAI(api_key=api_key), model_cfg
    except Exception:
        return None, model_cfg

"""Helpers for module 12 — blog strategy and interlinking."""

import re
import unicodedata
from urllib.parse import urlparse


def normalize_terms(value: str) -> set[str]:
    tokens = []
    for part in str(value).lower().replace("-", " ").replace("/", " ").split():
        token = "".join(ch for ch in part if ch.isalnum())
        if len(token) > 3:
            tokens.append(token)
    return set(tokens)


def slugify(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len].rstrip("-")


def url_path(url: str) -> str:
    path = urlparse(str(url)).path or "/"
    return path if path.endswith("/") else path + "/"


def classify_url(path: str, blog_prefix: str, service_prefix: str = "/service/") -> str:
    p = path.lower()
    if blog_prefix.lower() in p:
        return "blog"
    if service_prefix.lower() in p:
        return "service"
    if p.rstrip("/") in {"/our-services", ""} or p == "/":
        return "hub"
    if any(x in p for x in ("/portfolio", "/contact-us", "/about-us")):
        return "other"
    if any(x in p for x in ("/uncategorized/", "/architecture/", "/building/", "/aesthetic/")):
        return "legacy_blog"
    return "other"


def _ascii_lower(text: str) -> str:
    return unicodedata.normalize("NFKD", str(text).lower()).encode("ascii", "ignore").decode("ascii")


def is_transactional_service_query(query: str, service_pages: list[dict] | None = None) -> bool:
    """True when a blog post would compete with an existing service or hub landing."""
    ql = _ascii_lower(query)
    blocked = (
        "interior design",
        "interior designer",
        "interior architect",
        "interiorismo",
        "interioristas",
        "diseno de interiores",
        "arquitectura de interiores",
        "architecture studio",
        "architecture company",
        "design agency",
        "design architect",
        "architect and interior",
        "interior design company",
        "interior design studio",
        "bespoke millwork",
        "millwork ibiza",
        "custom furniture",
        "studio rethink",
        "web design",
        "design ibiza",
        "diseno ibiza",
        "diseño ibiza",
        "architect ibiza",
        "ibiza architect",
        "architects ibiza",
        "architects in ibiza",
        "design studio ibiza",
        "design company ibiza",
        "services in ibiza",
        "estudio creativo",
    )
    if any(term in ql for term in blocked):
        return True
    for svc in service_pages or []:
        path = str(svc.get("path", "")).lower().replace("-", " ")
        slug = path.strip("/").split("/")[-1]
        if slug and slug.replace("-", " ") in ql:
            return True
        for anchor in svc.get("anchors", []):
            if _ascii_lower(anchor) in ql:
                return True
    return False


def title_from_query(query: str) -> str:
    q = query.strip()
    if not q:
        return "Blog post"
    return q.title() if q.islower() else q[0].upper() + q[1:]


def coverage_ratio(query: str, page_terms: set[str]) -> float:
    q_terms = normalize_terms(query)
    if not q_terms:
        return 0.0
    return len(q_terms & page_terms) / len(q_terms)


def best_matching_page(
    query: str,
    pages: list[dict],
) -> tuple[dict | None, float]:
    q_terms = normalize_terms(query)
    if not q_terms:
        return None, 0.0
    best: dict | None = None
    best_score = 0.0
    for page in pages:
        page_terms = set()
        page_terms.update(normalize_terms(page.get("title", "")))
        page_terms.update(normalize_terms(page.get("primary_h1", "")))
        page_terms.update(normalize_terms(page.get("topic_keywords", "")))
        score = len(q_terms & page_terms) / len(q_terms)
        if score > best_score:
            best_score = score
            best = page
    return best, best_score

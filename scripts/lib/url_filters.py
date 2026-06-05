"""Filter crawl URLs to real HTML pages (exclude WP assets)."""

from urllib.parse import urlparse

ASSET_PATH_MARKERS = (
    "/wp-content/",
    "/wp-includes/",
    "/wp-admin/",
)

ASSET_EXTENSIONS = (
    ".js",
    ".css",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".map",
    ".ico",
    ".pdf",
    ".xml",
)


def is_html_page_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    path = (parsed.path or "/").lower()
    for marker in ASSET_PATH_MARKERS:
        if marker in path:
            return False
    for ext in ASSET_EXTENSIONS:
        if path.endswith(ext) or f"{ext}?" in path:
            return False
    return True

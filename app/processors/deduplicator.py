"""URL normalization and content deduplication utilities."""

import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Query parameters commonly used for tracking that should be stripped
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "source",
    "ncid",
}


def normalize_url(raw_url: str) -> str:
    """Normalize a URL by stripping tracking parameters, converting to lowercase scheme/host,
    and removing trailing slashes.
    """
    if not raw_url:
        return ""

    parsed = urlparse(raw_url.strip())
    query_dict = parse_qs(parsed.query, keep_blank_values=False)

    # Filter out tracking params
    filtered_query = {k: v for k, v in query_dict.items() if k.lower() not in TRACKING_PARAMS}

    clean_query = urlencode(filtered_query, doseq=True)

    # Strip trailing slash from path unless it's just root '/'
    path = parsed.path
    if path and path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            clean_query,
            "",  # Drop fragment
        )
    )
    return normalized


def compute_article_hash(title: str, url: str) -> str:
    """Generate a combined deterministic hash for an article."""
    canonical_url = normalize_url(url)
    clean_title = re.sub(r"\W+", "", title.lower())
    payload = f"{canonical_url}|{clean_title}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

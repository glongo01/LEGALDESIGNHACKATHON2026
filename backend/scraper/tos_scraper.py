"""
ToS fetcher and cleaner.
Priority: ToSDR API → homepage link discovery → canonical paths → failed.
"""

import re
import time
import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LEXIA-Bot/1.0; +https://github.com/LEXIA-Hackathon)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 15
MAX_CHARS = 12_000

POLICY_KEYWORDS = [
    "privacy", "privacy policy", "privacy notice", "datenschutz",
    "terms", "terms of service", "terms of use", "terms and conditions",
    "legal", "tos", "cookie policy", "user agreement", "data policy",
]

CANONICAL_PATHS = [
    "/privacy", "/privacy-policy", "/privacy_policy",
    "/legal/privacy", "/legal/privacy-policy",
    "/terms", "/terms-of-service", "/terms-of-use",
    "/legal", "/legal/terms",
]

REMOVE_TAGS = {"nav", "footer", "header", "script", "style", "aside", "noscript"}

# Known privacy/ToS URLs that bypass discovery for tricky sites
KNOWN_POLICY_URLS = {
    # Ordered lists: first URL that returns > 200 chars wins
    "facebook.com":  [
        "https://mbasic.facebook.com/privacy/policy/",
        "https://www.facebook.com/legal/terms/plain_text_terms",
    ],
    "meta.com":      ["https://mbasic.facebook.com/privacy/policy/"],
    "twitter.com":   ["https://twitter.com/en/privacy"],
    "x.com":         ["https://twitter.com/en/privacy"],
    "klarna.com":    [
        "https://cdn.klarna.com/1.0/shared/content/legal/terms/en/privacy",
        "https://www.klarna.com/us/legal/privacy-notice/",
    ],
    "anthropic.com": ["https://www.anthropic.com/legal/privacy"],
    "openai.com":    [
        "https://openai.com/policies/privacy-policy/",
        "https://openai.com/privacy/",
    ],
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(REMOVE_TAGS):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:MAX_CHARS]


def _try_tosdr(domain: str, session: requests.Session) -> dict | None:
    """Query ToSDR search API; return points list or None."""
    try:
        url = f"https://api.tosdr.org/search/v4/?query={domain}"
        r = session.get(url, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        data = r.json()
        services = data.get("parameters", {}).get("services", [])
        if not services:
            return None
        svc = services[0]
        points = svc.get("points", [])
        urls = svc.get("urls", [])
        policy_url = urls[0] if urls else None
        return {"points": points, "policy_url": policy_url, "name": svc.get("name", domain)}
    except Exception as e:
        logger.warning("ToSDR lookup failed for %s: %s", domain, e)
        return None


def _discover_policy_url(homepage: str, session: requests.Session) -> str | None:
    """Scan homepage footer links for a privacy/ToS URL."""
    try:
        r = session.get(homepage, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            text = (a.get_text() or "").lower()
            if any(kw in href or kw in text for kw in POLICY_KEYWORDS):
                full = urljoin(homepage, a["href"])
                if urlparse(full).scheme in ("http", "https"):
                    return full
    except Exception as e:
        logger.warning("Homepage discovery failed for %s: %s", homepage, e)
    return None


def _try_canonical_paths(domain: str, session: requests.Session) -> tuple[str | None, str | None]:
    """Try canonical paths; return (url, text) of first successful fetch."""
    base = f"https://{domain}"
    for path in CANONICAL_PATHS:
        url = base + path
        try:
            r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 500:
                return url, _clean_html(r.text)
        except Exception:
            continue
    return None, None


def _fetch_text(url: str, session: requests.Session) -> str | None:
    try:
        r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200:
            return _clean_html(r.text)
    except Exception as e:
        logger.warning("Fetch failed for %s: %s", url, e)
    return None


def scrape_tos(domain: str) -> dict:
    """
    Fetch ToS/privacy policy for a domain.

    Returns:
        {
            "domain": str,
            "source": "tosdr" | "scraped" | "failed",
            "policy_url": str | None,
            "text": str,
            "tosdr_points": list | None
        }
    """
    domain = domain.lower().strip().removeprefix("www.")
    session = _session()

    # 0. Use known policy URLs for well-known platforms (avoids JS-rendered failures)
    if domain in KNOWN_POLICY_URLS:
        candidates = KNOWN_POLICY_URLS[domain]
        for policy_url in candidates:
            text = _fetch_text(policy_url, session)
            if text and len(text) > 200:
                return {
                    "domain": domain,
                    "source": "scraped",
                    "policy_url": policy_url,
                    "text": text,
                    "tosdr_points": None,
                }

    # 1. Try ToSDR
    tosdr = _try_tosdr(domain, session)
    if tosdr and tosdr["points"]:
        policy_url = tosdr.get("policy_url")
        text = ""
        if policy_url:
            text = _fetch_text(policy_url, session) or ""
        if not text:
            # Build a synthetic text from ToSDR points
            lines = []
            for p in tosdr["points"]:
                title = p.get("title", "")
                qs = p.get("quoteStart", "")
                if title:
                    lines.append(title)
                if qs:
                    lines.append(qs)
            text = "\n".join(lines)[:MAX_CHARS]
        return {
            "domain": domain,
            "source": "tosdr",
            "policy_url": policy_url,
            "text": text,
            "tosdr_points": tosdr["points"],
        }

    # 2. Discover from homepage
    homepage = f"https://{domain}"
    policy_url = _discover_policy_url(homepage, session)
    if policy_url:
        text = _fetch_text(policy_url, session)
        if text:
            return {
                "domain": domain,
                "source": "scraped",
                "policy_url": policy_url,
                "text": text,
                "tosdr_points": None,
            }

    # 3. Try canonical paths
    policy_url, text = _try_canonical_paths(domain, session)
    if text:
        return {
            "domain": domain,
            "source": "scraped",
            "policy_url": policy_url,
            "text": text,
            "tosdr_points": None,
        }

    return {
        "domain": domain,
        "source": "failed",
        "policy_url": None,
        "text": "",
        "tosdr_points": None,
    }

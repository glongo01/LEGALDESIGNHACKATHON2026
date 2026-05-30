"""
scrape_tosdr.py
───────────────
scrapes privacy policies and terms of service from the ToS;DR public API
for a curated list of companies relevant to EU AI Act compliance research.

for each company it runs three steps:
  1. search by domain → get the tosdr service id
  2. fetch the full service record (includes pre-reviewed points[])
  3. fetch each linked document (includes the full .text field)

output lands in tosdr_data/, one folder per company:

  tosdr_data/
  ├── index.json          ← flat summary of everything scraped
  ├── openai/
  │   ├── service.json    ← full service object with points[]
  │   ├── privacy_policy.json
  │   └── terms_of_use.json
  ├── google/
  │   └── ...
  └── ...

re-runs are safe — already-fetched files load from cache and are skipped.

usage
─────
  pip install requests
  python scrape_tosdr.py               # scrape everything
  python scrape_tosdr.py --dry-run     # search only, no API calls / disk writes
  python scrape_tosdr.py --delay 1.0   # be more polite to the API
  python scrape_tosdr.py --companies openai.com google.com   # just these two
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import requests


# --- config ------------------------------------------------------------------

BASE_URL = "https://api.tosdr.org"
OUT_DIR  = Path(__file__).parent / "tosdr_data"

# the main list — picked because they all do something with AI that's
# relevant to the EU AI Act: chatbots, automated decisions, profiling,
# recommendation engines, credit scoring, voice/image generation, etc.
#
# a few things worth knowing:
#   - use facebook.com not meta.com (tosdr indexes them under facebook)
#   - zalando.com isn't in the tosdr database yet
#   - microsoft.com resolves to "Microsoft Store" (narrow scope, but ok)
#   - fico.com resolves to a wrong match (Glifico) — left out on purpose
COMPANIES = [

    # --- big tech & social ---------------------------------------------------
    # these are the obvious ones. heavy AI use, lots of profiling,
    # and most of them have an E rating from tosdr already.

    "openai.com",       # chatgpt, dall-e — the most obvious eu ai act target
    "google.com",       # search, maps, youtube — pervasive profiling
    "microsoft.com",    # copilot, azure ai — enterprise + consumer
    "facebook.com",     # meta ai, ad targeting, content moderation ai
    "apple.com",        # siri, app store recommendations
    "amazon.com",       # alexa, recommendations, aws ai — has a dedicated
                        # generative ai disclosure doc which is rare
    "twitter.com",      # x — algorithmic feed, 103 tosdr bad points, 5 blockers
    "linkedin.com",     # job recommendations, ai-based matching
    "tiktok.com",       # recommendation algorithm, has eu-specific ToS
                        # and a separate "privacy policy for younger users"
    "snapchat.com",     # lenses (ar/ai), content moderation
    "reddit.com",       # content ranking, 99 tosdr points — worth checking
    "discord.com",      # content moderation ai, community tools

    # --- ai-native companies -------------------------------------------------
    # these are the ones that actually build and deploy the models.
    # most have N/A tosdr ratings because they're too new to be reviewed,
    # but the documents themselves are the interesting part.

    "anthropic.com",    # claude — should have responsible use policy
    "midjourney.com",   # image generation — art. 52(3) watermarking relevant
    "character.ai",     # conversational ai — art. 50(1) disclosure relevant
    "perplexity.ai",    # ai search — sources + hallucination liability
    "synthesia.io",     # ai avatar video generation — deepfake adjacent,
                        # very relevant for art. 52(3) disclosure obligations

    # --- fintech & credit ----------------------------------------------------
    # automated credit decisions and financial profiling fall squarely into
    # annex III high-risk AI. klarna and revolut use AI for buy-now-pay-later
    # decisions. experian IS the credit scoring infrastructure.

    "paypal.com",       # payment fraud AI, algorithmic limits
    "klarna.com",       # buy-now-pay-later scoring — annex III employment/credit
    "revolut.com",      # neobank, AI fraud detection, EU operations
    "experian.com",     # credit bureau — annex III high-risk, algorithmic scoring

    # --- travel & gig economy ------------------------------------------------
    # dynamic pricing algorithms and algorithmic dispatch are both relevant
    # to art. 22 gdpr (automated decisions) and annex III.

    "uber.com",         # surge pricing algorithm, driver dispatch AI
    "airbnb.com",       # dynamic pricing, trust & safety AI
    "booking.com",      # recommendation engine, 39 bad points

    # --- entertainment -------------------------------------------------------
    # recommendation engines at massive scale. netflix's algorithm affects
    # what content gets seen; spotify's affects what music gets discovered.

    "netflix.com",      # recommendation engine, content personalisation
    "spotify.com",      # music recommendations, podcast AI

    # --- hr & employment screening -------------------------------------------
    # annex III explicitly lists employment-related AI as high-risk.
    # workday is used by most large enterprises for hr decisions.

    "workday.com",      # hr AI, workforce management, performance scoring
]


# companies we checked that AREN'T in the tosdr database yet.
# listed here for transparency — you'd need to scrape these directly
# from their websites rather than via tosdr.
#
# most of them are too new (post-2023 ai wave) or too niche for tosdr's
# volunteer reviewers to have gotten to them yet.
NOT_IN_TOSDR = {
    # generative ai tools
    "huggingface.co":   "model hub, has terms around ai output use",
    "stability.ai":     "stable diffusion — image gen, art. 52 relevant",
    "mistral.ai":       "eu-based llm — most likely to reference ai act directly",
    "runwayml.com":     "video generation AI",
    "elevenlabs.io":    "voice cloning — art. 52(3) synthetic voice disclosure",
    "cohere.com":       "enterprise llm",
    "replicate.com":    "model hosting platform",

    # tools with embedded AI
    "adobe.com":        "has a dedicated firefly ai addendum — very useful",
    "canva.com":        "ai image generation built in",
    "notion.so":        "notion AI, updated ToS in 2023",
    "grammarly.com":    "ai writing assistant at massive scale",
    "jasper.ai":        "ai copywriting",

    # eu-relevant companies
    "sap.com":          "german enterprise software, ai act compliance docs likely",
    "aleph-alpha.com":  "german llm startup — almost certainly references ai act",
    "doctolib.fr":      "french health AI — annex III high-risk (medical diagnosis)",
    "criteo.com":       "french ad-tech AI",

    # high-risk AI use cases (annex III)
    "hirevue.com":      "AI video interviewing — employment screening, annex III",
    "fico.com":         "credit scoring algorithms — annex III (note: tosdr match is wrong)",
    "clearview.ai":     "facial recognition — art. 5 prohibited practices territory",
}

HEADERS = {"Accept": "application/json", "User-Agent": "eu-ai-act-research/0.1"}


# --- helpers -----------------------------------------------------------------

def slugify(text: str) -> str:
    # turns "Privacy Policy (EU)" into "privacy_policy_eu" etc.
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def get(session: requests.Session, url: str, delay: float, retries: int = 3) -> dict | None:
    # simple GET with retry on rate limits. returns None on any failure
    # so callers don't have to deal with exceptions.
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"    ⚠ rate limited — waiting {wait}s …")
                time.sleep(wait)
                continue
            if resp.status_code == 404:
                return None
            print(f"    ✗ HTTP {resp.status_code} for {url}")
            return None
        except requests.RequestException as exc:
            print(f"    ✗ request error: {exc}")
            if attempt < retries - 1:
                time.sleep(2)
    return None


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# --- core pipeline -----------------------------------------------------------

def search_service(session, query: str, delay: float) -> dict | None:
    # step 1: turn a domain like "openai.com" into a tosdr service record
    url  = f"{BASE_URL}/search/v5?query={requests.utils.quote(query)}"
    data = get(session, url, delay)
    time.sleep(delay)
    if not data or not data.get("services"):
        return None
    return data["services"][0]  # first result is usually the right one


def fetch_service_detail(session, service_id: int, delay: float) -> dict | None:
    # step 2: get the full service object — this includes the documents[]
    # list AND the pre-reviewed points[], which are free compliance signal
    url  = f"{BASE_URL}/service/v3?id={service_id}"
    data = get(session, url, delay)
    time.sleep(delay)
    return data


def fetch_document(session, doc_id: int, delay: float) -> dict | None:
    # step 3: fetch one document — the .text field has the full policy text
    url  = f"{BASE_URL}/document/v2?id={doc_id}"
    data = get(session, url, delay)
    time.sleep(delay)
    return data


def scrape_company(session, query: str, delay: float, dry_run: bool) -> dict | None:
    """run the full pipeline for one company and return an index entry."""

    print(f"\n{'─'*55}")
    print(f"  🔍  {query}")

    # search
    match = search_service(session, query, delay)
    if not match:
        print(f"  ✗  not found in tosdr")
        return None

    service_id   = match["id"]
    service_name = match["name"]
    rating       = match.get("rating", "?")
    folder       = match.get("slug") or slugify(service_name)
    company_dir  = OUT_DIR / folder
    print(f"  ✓  {service_name}  (id={service_id}, rating={rating})  → {folder}/")

    # service detail — load from cache if we already have it
    service_path = company_dir / "service.json"
    if service_path.exists() and not dry_run:
        print(f"  ↩  already scraped — loading from cache")
        detail = json.loads(service_path.read_text())
    else:
        detail = fetch_service_detail(session, service_id, delay)
        if not detail:
            print(f"  ✗  could not fetch service detail")
            return None
        if not dry_run:
            save_json(service_path, detail)
            print(f"  💾  saved service → {folder}/service.json")

    docs_meta   = detail.get("documents", [])
    points      = detail.get("points", [])
    bad_points  = [p for p in points if p.get("case", {}).get("classification") == "bad"]
    blocker_pts = [p for p in points if p.get("case", {}).get("classification") == "blocker"]

    print(f"  📄  {len(docs_meta)} document(s) | "
          f"{len(points)} points ({len(blocker_pts)} blockers, {len(bad_points)} bad)")

    if dry_run:
        return {"query": query, "service_id": service_id, "name": service_name,
                "rating": rating, "documents": [], "n_points": len(points)}

    # fetch each linked document
    saved_docs = []
    used_filenames: set[str] = set()

    for doc_ref in docs_meta:
        doc_id   = doc_ref["id"]
        doc_name = doc_ref.get("name", f"document_{doc_id}")

        # clean up the filename — strip [DEPRECATED] prefix and deduplicate
        clean_name = re.sub(r"^\[deprecated\]\s*", "", doc_name, flags=re.IGNORECASE)
        base       = slugify(clean_name) or f"document_{doc_id}"
        filename   = base if base != "service" else f"{base}_doc"
        if filename in used_filenames:
            filename = f"{filename}_{doc_id}"  # append id to break the tie
        used_filenames.add(filename)

        doc_path = company_dir / f"{filename}.json"

        if doc_path.exists():
            print(f"    ↩  {doc_name} — cached")
            doc = json.loads(doc_path.read_text())
        else:
            doc = fetch_document(session, doc_id, delay)
            if not doc:
                print(f"    ✗  failed to fetch {doc_id} ({doc_name})")
                continue
            save_json(doc_path, doc)
            text_len = len(doc.get("text") or "")
            print(f"    💾  {doc_name} — {text_len:,} chars → {folder}/{filename}.json")

        saved_docs.append({
            "id":          doc["id"],
            "name":        doc.get("name"),
            "url":         doc.get("url"),
            "text_length": len(doc.get("text") or ""),
            "file":        str(doc_path),
        })

    return {
        "query":      query,
        "service_id": service_id,
        "name":       service_name,
        "slug":       folder,
        "rating":     rating,
        "is_comprehensively_reviewed": detail.get("is_comprehensively_reviewed", False),
        "n_points":   len(points),
        "n_blockers": len(blocker_pts),
        "n_bad":      len(bad_points),
        "documents":  saved_docs,
        "service_file": str(service_path),
    }


# --- main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="scrape tosdr for a curated list of AI-relevant companies."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="search only — no document fetches or disk writes")
    parser.add_argument("--delay", type=float, default=0.6,
                        help="seconds between API calls (default: 0.6)")
    parser.add_argument("--companies", nargs="+", metavar="DOMAIN",
                        help="override the built-in list with specific domains")
    args = parser.parse_args()

    companies = args.companies or COMPANIES

    print(f"\n{'═'*55}")
    print(f"  ToS;DR Scraper — {len(companies)} companies")
    print(f"  delay: {args.delay}s | dry-run: {args.dry_run}")
    print(f"  output: {OUT_DIR.resolve()}")
    if NOT_IN_TOSDR:
        print(f"  (+ {len(NOT_IN_TOSDR)} companies not in tosdr — see NOT_IN_TOSDR dict)")
    print(f"{'═'*55}")

    OUT_DIR.mkdir(exist_ok=True)
    index_path = OUT_DIR / "index.json"

    # load existing index so re-runs just add to it rather than overwriting
    index: dict[str, dict] = {}
    if index_path.exists():
        index = {e["query"]: e for e in json.loads(index_path.read_text())}

    session = requests.Session()
    results = []

    for query in companies:
        entry = scrape_company(session, query, args.delay, args.dry_run)
        if entry:
            results.append(entry)
            index[query] = entry

    # write index
    if not args.dry_run:
        index_path.write_text(
            json.dumps(list(index.values()), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # summary
    found        = [r for r in results if r]
    total_docs   = sum(len(r.get("documents", [])) for r in found)
    total_chars  = sum(d.get("text_length", 0) for r in found for d in r.get("documents", []))
    total_points = sum(r.get("n_points", 0) for r in found)

    print(f"\n{'═'*55}")
    print(f"  done. {len(found)}/{len(companies)} services found")
    print(f"  {total_docs} documents  ({total_chars:,} chars ≈ {total_chars//4:,} tokens)")
    print(f"  {total_points} pre-reviewed tosdr points total")
    if not args.dry_run:
        print(f"  index → {index_path}")
    print(f"{'═'*55}\n")

    print(f"  {'Company':<22} {'Rating':<8} {'Docs':<6} {'Pts':<6} {'Blockers'}")
    print(f"  {'─'*22} {'─'*8} {'─'*6} {'─'*6} {'─'*8}")
    for r in sorted(found, key=lambda x: x.get("rating") or "Z"):
        print(f"  {r['name']:<22} {r.get('rating','?'):<8} "
              f"{len(r.get('documents',[])):<6} "
              f"{r.get('n_points',0):<6} "
              f"{r.get('n_blockers',0)}")


if __name__ == "__main__":
    main()

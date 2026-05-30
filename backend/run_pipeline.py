"""
One-shot pipeline: scrape, extract, score, and save 5 pre-defined platforms.
Run: python backend/run_pipeline.py
Requires: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY env vars.
"""

import json
import logging
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from backend.scraper.tos_scraper import scrape_tos
from backend.scraper.tos_extractor import extract
from backend.scraper.wikidata_client import get_platform_metadata
from backend.semaphore import compute_semaphore
from backend.ontology.kg_builder import get_article_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PLATFORMS = [
    "openai.com",
    "twitter.com",
    "klarna.com",
    "anthropic.com",
    "facebook.com",
]

OUTPUT_DIR = pathlib.Path(__file__).parent / "data" / "platforms"
MAPPING_PATH = pathlib.Path(__file__).parent / "ontology" / "concept_akn_mapping.json"

# Pre-downloaded ToSDR JSON files (from glongo01/LEGALDESIGNHACKATHON2026)
_TOSDR_REPO = pathlib.Path.home() / "Downloads" / "LEGALDESIGNHACKATHON2026-main" / "tosdr_data"
TOSDR_SOURCES = {
    "openai.com":    [_TOSDR_REPO / "openai" / "privacy_policy.json",
                      _TOSDR_REPO / "openai" / "terms_of_use.json"],
    "twitter.com":   [],   # not in repo — use scraper
    "klarna.com":    [_TOSDR_REPO / "klarna" / "privacy.json",
                      _TOSDR_REPO / "klarna" / "legal.json"],
    "anthropic.com": [_TOSDR_REPO / "anthropic_pbc" / "privacy_policy.json",
                      _TOSDR_REPO / "anthropic_pbc" / "terms_of_service.json"],
    "facebook.com":  [_TOSDR_REPO / "facebook" / "privacy_policy.json",
                      _TOSDR_REPO / "facebook" / "terms_of_service.json"],
}
MAX_CHARS = 14_000


def _load_tosdr_text(domain: str) -> tuple[str | None, str | None]:
    """Load pre-downloaded ToSDR text. Returns (text, url)."""
    sources = TOSDR_SOURCES.get(domain, [])
    parts, url = [], None
    for path in sources:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            text = data.get("text", "")
            if not url:
                url = data.get("url", "")
            if text:
                parts.append(text)
        except Exception:
            continue
    combined = "\n\n".join(parts)[:MAX_CHARS] if parts else None
    return combined, url


def load_mapping() -> dict:
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_platform_json(
    domain: str,
    metadata: dict,
    extraction: dict,
    sem: dict,
    mapping: dict,
    policy_url: str | None = None,
) -> dict:
    concepts = mapping["concepts"]

    rights = []
    risks = []

    for cid, concept in concepts.items():
        entry = extraction.get(cid, {"status": "unknown", "evidence": None, "confidence": "low"})
        primary_ref = concept["akn_refs"][0] if concept["akn_refs"] else {}

        # Enrich akn_ref text from XML if not already present
        ref_text = primary_ref.get("text", "")
        if not ref_text:
            ref_text = get_article_text(
                primary_ref.get("eid", ""), primary_ref.get("celex", "")
            )

        akn_ref = {
            "eid": primary_ref.get("eid", ""),
            "article": primary_ref.get("article", ""),
            "regulation": primary_ref.get("regulation", ""),
            "text": ref_text,
            "highlight_start": primary_ref.get("highlight_start", 0),
            "highlight_end": primary_ref.get("highlight_end", len(ref_text)),
            "official_url": primary_ref.get("official_url", ""),
        }

        # All references (for multi-source panel in popup)
        all_akn_refs = []
        for ref in concept.get("akn_refs", []):
            t = ref.get("text", "") or get_article_text(ref.get("eid", ""), ref.get("celex", ""))
            all_akn_refs.append({
                "eid": ref.get("eid", ""),
                "article": ref.get("article", ""),
                "regulation": ref.get("regulation", ""),
                "relevance": ref.get("relevance", "primary"),
                "text": t,
                "highlight_start": ref.get("highlight_start", 0),
                "highlight_end": ref.get("highlight_end", len(t)),
                "official_url": ref.get("official_url", ""),
            })

        card = {
            "id": cid,
            "label": concept["label"],
            "label_child": concept["label_child"],
            "description": concept["description"],
            "description_child": concept["description_child"],
            "concept": concept["concept"],
            "evidence": entry.get("evidence"),
            "confidence": entry.get("confidence", "low"),
            "akn_ref": akn_ref,
            "akn_refs": all_akn_refs,
        }

        if concept["category"] == "right":
            card["status"] = entry.get("status", "unknown")
            rights.append(card)
        else:
            status = entry.get("status", "unknown")
            # For risk concepts: "granted" = practice confirmed = show as detected risk
            severity = concept.get("severity_default", "medium")
            # Downgrade severity if status is unknown
            if status == "unknown":
                severity = "low"
            elif status == "violated":
                # Risk was explicitly denied — not a problem
                severity = "low"
            card["severity"] = severity
            card["detected"] = status == "granted"
            risks.append(card)

    # Only include risks that are detected or unknown (not explicitly denied)
    visible_risks = [r for r in risks if r.get("detected") or r.get("severity") != "low"]
    # Always show all rights
    all_rights = rights

    return {
        "site": {
            "domain": domain,
            "name": metadata.get("name", domain),
            "favicon_letter": metadata.get("name", domain)[0].upper(),
            "system_type": metadata.get("system_type", "general_ai_system"),
            "country": metadata.get("country", "Unknown"),
            "founded": metadata.get("founded"),
            "wikidata_id": metadata.get("wikidata_id", ""),
            "policy_url": policy_url,
            "semaphore": sem["semaphore"],
            "semaphore_score": sem["semaphore_score"],
            "semaphore_label": sem["semaphore_label"],
            "score_breakdown": sem.get("score_breakdown", []),
            "score_formula": sem.get("score_formula", ""),
        },
        "rights": all_rights,
        "risks": visible_risks,
        "mode": "adult",
    }


def process_platform(domain: str, mapping: dict, force: bool = False) -> dict:
    logger.info("── Processing %s", domain)

    output_path = OUTPUT_DIR / f"{domain}.json"
    if output_path.exists():
        logger.info("  [CACHE] %s already processed, loading from disk", domain)
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 1. Load ToS — prefer pre-downloaded ToSDR data, fallback to live scrape
    logger.info("  [1/4] Loading ToS...")
    tosdr_text, tosdr_url = _load_tosdr_text(domain)
    if tosdr_text:
        tos = {"domain": domain, "source": "tosdr_local", "policy_url": tosdr_url,
               "text": tosdr_text, "tosdr_points": None}
        logger.info("  Source: tosdr_local | URL: %s | Text: %d chars",
                     tosdr_url or "—", len(tosdr_text))
    else:
        tos = scrape_tos(domain)
        logger.info("  Source: %s | URL: %s | Text: %d chars",
                     tos["source"], tos.get("policy_url", "—"), len(tos["text"]))

    # 2. Extract rights/risks
    logger.info("  [2/4] Extracting with Azure OpenAI...")
    extraction = extract(tos["text"])

    # 3. Wikidata metadata
    logger.info("  [3/4] Fetching Wikidata metadata...")
    metadata = get_platform_metadata(domain)
    logger.info("  Name: %s | Type: %s | Country: %s",
                 metadata["name"], metadata["system_type"], metadata["country"])

    # 4. Compute semaphore (pass system_type to calibrate AI-specific weights)
    logger.info("  [4/4] Computing semaphore...")
    sem = compute_semaphore(extraction, system_type=metadata.get("system_type", "general_ai_system"))
    logger.info("  Score: %d | Color: %s | %s",
                 sem["semaphore_score"], sem["semaphore"].upper(), sem["semaphore_label"])

    # Build and save
    result = build_platform_json(domain, metadata, extraction, sem, mapping, policy_url=tos.get("policy_url"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    logger.info("  Saved → %s", output_path)

    return result


def main():
    mapping = load_mapping()
    results = {}

    print("\n" + "=" * 60)
    print("LEXIA Pipeline — Processing 5 platforms")
    print("=" * 60 + "\n")

    for domain in PLATFORMS:
        try:
            result = process_platform(domain, mapping)
            results[domain] = result
        except Exception as e:
            logger.error("FAILED %s: %s", domain, e, exc_info=True)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Domain':<20} {'Color':<8} {'Score':<8} {'Rights':<8} {'Risks'}")
    print("-" * 60)
    for domain, r in results.items():
        site = r.get("site", {})
        color = site.get("semaphore", "—")
        score = site.get("semaphore_score", "—")
        nrights = len(r.get("rights", []))
        nrisks = len(r.get("risks", []))
        print(f"{domain:<20} {color:<8} {str(score):<8} {nrights:<8} {nrisks}")
    print()


if __name__ == "__main__":
    main()

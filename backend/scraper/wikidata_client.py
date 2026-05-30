"""
Wikidata SPARQL client — fetches platform metadata for a domain.
"""

import logging
import re

import requests

logger = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "LEXIA-Bot/1.0 (https://github.com/LEXIA-Hackathon; contact@lexia.eu)",
    "Accept": "application/sparql-results+json",
}
TIMEOUT = 20

AIRO_TYPE_MAP = {
    "chatbot": "conversational_ai",
    "virtual assistant": "conversational_ai",
    "social network": "social_network",
    "social media": "social_network",
    "social networking service": "social_network",
    "social networking website": "social_network",
    "search engine": "search_engine",
    "image generation software": "generative_ai",
    "large language model": "conversational_ai",
    "online marketplace": "marketplace",
    "e-commerce": "marketplace",
    "artificial intelligence": "conversational_ai",
    "artificial intelligence company": "conversational_ai",
    "artificial intelligence assistant": "conversational_ai",
    "messenger": "social_network",
    "microblogging": "social_network",
}

DOMAIN_FALLBACKS = {
    "openai.com": {
        "name": "OpenAI",
        "instance_of": "artificial intelligence company",
        "system_type": "conversational_ai",
        "country": "United States",
        "founded": "2015",
        "wikidata_id": "Q21708238",
    },
    "twitter.com": {
        "name": "X (Twitter)",
        "instance_of": "social networking service",
        "system_type": "social_network",
        "country": "United States",
        "founded": "2006",
        "wikidata_id": "Q918",
    },
    "klarna.com": {
        "name": "Klarna",
        "instance_of": "financial technology company",
        "system_type": "marketplace",
        "country": "Sweden",
        "founded": "2005",
        "wikidata_id": "Q2416929",
    },
    "anthropic.com": {
        "name": "Anthropic",
        "instance_of": "artificial intelligence company",
        "system_type": "conversational_ai",
        "country": "United States",
        "founded": "2021",
        "wikidata_id": "Q115051868",
    },
    "facebook.com": {
        "name": "Facebook",
        "instance_of": "social networking service",
        "system_type": "social_network",
        "country": "United States",
        "founded": "2004",
        "wikidata_id": "Q355",
    },
}


def _map_system_type(instance_of: str) -> str:
    lower = instance_of.lower()
    for keyword, airo_type in AIRO_TYPE_MAP.items():
        if keyword in lower:
            return airo_type
    return "general_ai_system"


def _sparql_query(domain: str) -> str:
    bare = domain.removeprefix("www.").split(".")[0]
    return f"""
SELECT DISTINCT ?item ?itemLabel ?instanceLabel ?countryLabel ?founded WHERE {{
  ?item wdt:P856 ?website .
  FILTER(CONTAINS(LCASE(STR(?website)), "{bare}"))
  OPTIONAL {{ ?item wdt:P31 ?instance . }}
  OPTIONAL {{ ?item wdt:P17 ?country . }}
  OPTIONAL {{ ?item wdt:P571 ?founded . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5
"""


def _run_sparql(query: str) -> list[dict]:
    try:
        r = requests.get(
            SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get("results", {}).get("bindings", [])
    except Exception as e:
        logger.warning("SPARQL query failed: %s", e)
        return []


def get_platform_metadata(domain: str) -> dict:
    """
    Return platform metadata for a domain.

    Returns:
        {
            "name": str,
            "instance_of": str,
            "system_type": str,   # AIRO vocab
            "country": str,
            "founded": str | None,
            "wikidata_id": str
        }
    """
    bare = domain.removeprefix("www.")

    # Use fallback for known platforms (avoids rate-limiting issues during demo)
    if bare in DOMAIN_FALLBACKS:
        return DOMAIN_FALLBACKS[bare]

    query = _sparql_query(bare)
    bindings = _run_sparql(query)

    if not bindings:
        return {
            "name": bare.split(".")[0].capitalize(),
            "instance_of": "online service",
            "system_type": "general_ai_system",
            "country": "Unknown",
            "founded": None,
            "wikidata_id": "",
        }

    row = bindings[0]
    name = row.get("itemLabel", {}).get("value", bare)
    instance_of = row.get("instanceLabel", {}).get("value", "online service")
    country = row.get("countryLabel", {}).get("value", "Unknown")
    wikidata_id = row.get("item", {}).get("value", "").split("/")[-1]

    founded = None
    if "founded" in row:
        raw = row["founded"]["value"]
        m = re.search(r"(\d{4})", raw)
        if m:
            founded = m.group(1)

    return {
        "name": name,
        "instance_of": instance_of,
        "system_type": _map_system_type(instance_of),
        "country": country,
        "founded": founded,
        "wikidata_id": wikidata_id,
    }

"""
Knowledge Graph builder — reads AKN XML + concept_akn_mapping.json
and emits an RDF-like in-memory graph as a plain dict.
"""

import json
import pathlib
import re
import xml.etree.ElementTree as ET

BASE = pathlib.Path(__file__).parent.parent.parent

AKN_NS = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
MAPPING_PATH = BASE / "backend" / "ontology" / "concept_akn_mapping.json"
AIA_XML = BASE / "32024R1689.xml"
GDPR_XML = BASE / "32016R0679.xml"

CELEX_TO_XML = {
    "32024R1689": AIA_XML,
    "32016R0679": GDPR_XML,
}


def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _extract_text_by_eid(tree: ET.ElementTree, eid: str) -> str:
    """Walk the XML tree and return the text content of the element with matching eId."""
    root = tree.getroot()
    for elem in root.iter():
        if elem.get("eId") == eid:
            parts = []
            for node in elem.iter():
                if _strip_ns(node.tag) == "p":
                    t = "".join(node.itertext()).strip()
                    if t:
                        parts.append(t)
            return " ".join(parts)
    return ""


def _load_xml(path: pathlib.Path) -> ET.ElementTree | None:
    try:
        return ET.parse(path)
    except Exception:
        return None


def build_kg() -> dict:
    """
    Build the LEXIA Knowledge Graph.

    Returns a dict with:
      - "concepts": concept metadata enriched with AKN article texts
      - "graph": triples list [ {"subject", "predicate", "object"} ]
    """
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    concepts = mapping["concepts"]
    xml_trees: dict[str, ET.ElementTree | None] = {}
    for celex, xml_path in CELEX_TO_XML.items():
        xml_trees[celex] = _load_xml(xml_path)

    enriched = {}
    triples = []

    for cid, concept in concepts.items():
        node = dict(concept)
        enriched_refs = []

        for ref in concept.get("akn_refs", []):
            celex = ref.get("celex", "")
            eid = ref.get("eid", "")
            tree = xml_trees.get(celex)

            ref_copy = dict(ref)
            if tree and eid:
                extracted = _extract_text_by_eid(tree, eid)
                if extracted:
                    ref_copy["text"] = extracted

            enriched_refs.append(ref_copy)

            # Emit triples
            triples.append({
                "subject": f"lexia:{cid}",
                "predicate": "hasLegalBasis",
                "object": f"akn:{celex}#{eid}",
            })
            triples.append({
                "subject": f"akn:{celex}#{eid}",
                "predicate": "inRegulation",
                "object": ref.get("regulation", ""),
            })

        node["akn_refs"] = enriched_refs
        enriched[cid] = node

        triples.append({
            "subject": f"lexia:{cid}",
            "predicate": "rdf:type",
            "object": f"lexia:{concept['category'].capitalize()}",
        })
        triples.append({
            "subject": f"lexia:{cid}",
            "predicate": "rdfs:label",
            "object": concept.get("label", ""),
        })

    return {
        "concepts": enriched,
        "graph": triples,
        "metadata": mapping.get("metadata", {}),
    }


def get_article_text(eid: str, celex: str) -> str:
    """Convenience: extract article text for a given eId and CELEX number."""
    xml_path = CELEX_TO_XML.get(celex)
    if not xml_path:
        return ""
    tree = _load_xml(xml_path)
    if not tree:
        return ""
    return _extract_text_by_eid(tree, eid)

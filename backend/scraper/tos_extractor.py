"""
Azure OpenAI-powered ToS extractor.
Maps ToS text to concept IDs defined in concept_akn_mapping.json.
"""

import json
import logging
import os
import pathlib

from openai import AzureOpenAI

logger = logging.getLogger(__name__)

_MAPPING_PATH = pathlib.Path(__file__).parent.parent / "ontology" / "concept_akn_mapping.json"


def _load_concepts() -> dict:
    with open(_MAPPING_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["concepts"]


def _build_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_version="2024-12-01-preview",
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
    )


def _build_concept_list(concepts: dict) -> str:
    lines = []
    for cid, c in concepts.items():
        category = c["category"].upper()
        label = c["label"]
        ref = c["akn_refs"][0]["article"] + " " + c["akn_refs"][0]["regulation"]
        lines.append(f'  - "{cid}" [{category}] "{label}" — {ref}')
    return "\n".join(lines)


def _build_prompt(tos_text: str, concepts: dict) -> str:
    concept_list = _build_concept_list(concepts)
    cids = list(concepts.keys())
    return f"""You are an EU AI Act compliance auditor. Analyse the Terms of Service / Privacy Policy text and determine the compliance status for each concept below.

CONCEPTS TO EVALUATE:
{concept_list}

TERMS OF SERVICE TEXT:
\"\"\"
{tos_text[:11000]}
\"\"\"

INSTRUCTIONS:
1. For each concept ID listed above, determine its status:
   - RIGHT concepts:
     * "granted" = the ToS or privacy policy explicitly confirms this right is provided to users.
     * "violated" = the ToS explicitly BLOCKS, DENIES, or WAIVES this right (e.g. "you waive your right to...", "we may make automated decisions without human review").
     * "unknown" = the ToS does not mention this right at all, or it is ambiguous. Use "unknown" when the right is simply absent from the document.
   - RISK concepts:
     * "granted" = the ToS explicitly CONFIRMS this practice occurs (e.g. "we use your data to train our models", "we share data with third parties for advertising").
     * "violated" = the ToS explicitly PROHIBITS this practice.
     * "unknown" = the ToS does not address this practice clearly.
   - Special rule for "no_ai_disclosure": if the ToS/privacy policy explicitly states users are informed they interact with AI → "violated" (i.e. the risk is mitigated). If the ToS does NOT mention AI interaction disclosure → "granted" (the risk is present). If ambiguous → "unknown".

2. For each concept provide:
   - "status": "granted" | "violated" | "unknown"
   - "evidence": exact quote from the ToS (≤120 chars) that supports your conclusion, or null if unknown
   - "confidence": "high" | "medium" | "low"

3. Output ONLY valid JSON — no preamble, no explanation, no markdown fences.

Required output format:
{{
{chr(10).join(f'  "{cid}": {{"status": "...", "evidence": "...", "confidence": "..."}},' for cid in cids)}
}}"""


def _empty_result(concepts: dict) -> dict:
    return {
        cid: {"status": "unknown", "evidence": None, "confidence": "low"}
        for cid in concepts
    }


def _parse_response(raw: str, concepts: dict) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    result = {}
    valid_statuses = {"granted", "violated", "unknown"}
    valid_confidences = {"high", "medium", "low"}

    for cid in concepts:
        entry = data.get(cid, {})
        status = entry.get("status", "unknown")
        if status not in valid_statuses:
            status = "unknown"
        evidence = entry.get("evidence")
        if evidence and len(str(evidence)) > 200:
            evidence = str(evidence)[:120]
        confidence = entry.get("confidence", "low")
        if confidence not in valid_confidences:
            confidence = "low"
        result[cid] = {"status": status, "evidence": evidence, "confidence": confidence}

    return result


def _repair_prompt(broken_response: str, concepts: dict) -> str:
    cids = list(concepts.keys())
    return f"""The following JSON is malformed or incomplete. Fix it so it is valid JSON with exactly these keys: {cids}.
Each value must have: "status" (granted|violated|unknown), "evidence" (string or null), "confidence" (high|medium|low).
Return ONLY the corrected JSON object.

Broken response:
{broken_response[:3000]}"""


def extract(tos_text: str) -> dict:
    """
    Extract rights/risks from ToS text using Azure OpenAI.

    Returns dict: concept_id → {"status", "evidence", "confidence"}
    """
    concepts = _load_concepts()

    if not tos_text or len(tos_text.strip()) < 50:
        logger.warning("ToS text too short, returning all unknown")
        return _empty_result(concepts)

    client = _build_client()
    prompt = _build_prompt(tos_text, concepts)

    # First attempt
    try:
        resp = client.chat.completions.create(
            model="o4-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=4000,
        )
        raw = resp.choices[0].message.content
        result = _parse_response(raw, concepts)
        if result is not None:
            return result
        logger.warning("First parse failed, attempting repair")
    except Exception as e:
        logger.error("Azure OpenAI call failed: %s", e)
        return _empty_result(concepts)

    # Retry with repair prompt
    try:
        repair = _repair_prompt(raw, concepts)
        resp2 = client.chat.completions.create(
            model="o4-mini",
            messages=[{"role": "user", "content": repair}],
            response_format={"type": "json_object"},
            max_completion_tokens=4000,
        )
        raw2 = resp2.choices[0].message.content
        result2 = _parse_response(raw2, concepts)
        if result2 is not None:
            return result2
    except Exception as e:
        logger.error("Repair attempt failed: %s", e)

    return _empty_result(concepts)

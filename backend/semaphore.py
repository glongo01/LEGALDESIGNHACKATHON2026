"""
Semaphore scoring: converts extraction results to a traffic-light score.
Weights are adjusted based on system_type (from Wikidata) so that
AI-specific risks only penalise platforms that actually deploy AI interaction.
"""

_BASE_RISK_WEIGHTS = {
    "training_on_user_data": 25,
    "profiling":             20,
    "third_party_sharing":   15,
}
_AI_DISCLOSURE_WEIGHT = 35

RIGHT_WEIGHTS = {
    "right_explanation":     25,
    "right_human_oversight": 20,
    "right_ai_transparency": 20,
    "right_complaint":       15,
}

_AI_DISCLOSURE_FACTOR = {
    "conversational_ai": 1.0,
    "general_ai_system": 0.8,
    "social_network":    0.6,
    "search_engine":     0.5,
    "marketplace":       0.3,
}

UNKNOWN_PENALTY_RATIO = 0.40
RIGHT_BONUS_RATIO     = 0.30
VIOLATION_MULTIPLIER  = 1.5

_LABELS = {
    "no_ai_disclosure":      "No AI Disclosure",
    "training_on_user_data": "Data used for training",
    "profiling":             "Automated profiling",
    "third_party_sharing":   "Third-party data sharing",
    "right_explanation":     "Right to Explanation",
    "right_human_oversight": "Right to Human Oversight",
    "right_ai_transparency": "Right to Know It's AI",
    "right_complaint":       "Right to Complain",
}


def _build_breakdown(risk_weights: dict, right_weights: dict, extraction: dict) -> list:
    rows = []
    for cid, weight in risk_weights.items():
        entry = extraction.get(cid, {})
        status = entry.get("status", "unknown")
        if status == "granted":
            delta = -weight
        elif status == "unknown":
            delta = -round(weight * UNKNOWN_PENALTY_RATIO)
        else:
            delta = 0
        rows.append({"id": cid, "label": _LABELS.get(cid, cid), "type": "risk",
                      "status": status, "delta": delta, "weight": weight})
    for cid, weight in right_weights.items():
        entry = extraction.get(cid, {})
        status = entry.get("status", "unknown")
        if status == "violated":
            delta = -round(weight * VIOLATION_MULTIPLIER)
        elif status == "granted":
            delta = +round(weight * RIGHT_BONUS_RATIO)
        else:
            delta = -round(weight * UNKNOWN_PENALTY_RATIO)
        rows.append({"id": cid, "label": _LABELS.get(cid, cid), "type": "right",
                      "status": status, "delta": delta, "weight": weight})
    return rows


def compute_semaphore(extraction: dict, system_type: str = "general_ai_system") -> dict:
    """
    Compute compliance semaphore from extraction results.

    Returns extended dict including score_breakdown and score_formula.
    """
    factor = _AI_DISCLOSURE_FACTOR.get(system_type, 0.7)
    risk_weights = dict(_BASE_RISK_WEIGHTS)
    risk_weights["no_ai_disclosure"] = round(_AI_DISCLOSURE_WEIGHT * factor)

    penalty = 0.0
    for cid, weight in risk_weights.items():
        status = extraction.get(cid, {}).get("status", "unknown")
        if status == "granted":
            penalty += weight
        elif status == "unknown":
            penalty += weight * UNKNOWN_PENALTY_RATIO

    right_bonus = 0.0
    for cid, weight in RIGHT_WEIGHTS.items():
        status = extraction.get(cid, {}).get("status", "unknown")
        if status == "violated":
            penalty += weight * VIOLATION_MULTIPLIER
        elif status == "granted":
            right_bonus += weight
        elif status == "unknown":
            penalty += weight * UNKNOWN_PENALTY_RATIO

    breakdown = _build_breakdown(risk_weights, RIGHT_WEIGHTS, extraction)
    raw = 100.0 - penalty + right_bonus * RIGHT_BONUS_RATIO
    score = int(max(0, min(100, round(raw))))

    if score >= 70:
        semaphore, label = "green",  "Good compliance detected"
    elif score >= 40:
        semaphore, label = "orange", "Partial compliance detected"
    else:
        semaphore, label = "red",    "Significant concerns detected"

    return {
        "semaphore": semaphore,
        "semaphore_score": score,
        "semaphore_label": label,
        "score_breakdown": breakdown,
        "score_formula": f"100 − {int(penalty)} pts penalties + {int(right_bonus * RIGHT_BONUS_RATIO)} pts bonus = {score}/100",
    }

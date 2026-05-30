"""
LEXIA Flask API — serves pre-processed platform data to the browser extension.
Run: python backend/api/app.py
Port: 5050
"""

import json
import pathlib

from flask import Flask, jsonify
from flask_cors import CORS

BASE = pathlib.Path(__file__).parent.parent
PLATFORMS_DIR = BASE / "data" / "platforms"
MAPPING_PATH = BASE / "ontology" / "concept_akn_mapping.json"

SUPPORTED_DOMAINS = ["openai.com", "twitter.com", "klarna.com", "anthropic.com", "facebook.com"]

# Domain aliases → canonical domain in data/platforms/
ALIASES = {
    "chatgpt.com":      "openai.com",
    "chat.openai.com":  "openai.com",
    "x.com":            "twitter.com",
    "instagram.com":    "facebook.com",
    "messenger.com":    "facebook.com",
    "meta.com":         "facebook.com",
    "claude.ai":        "anthropic.com",
    "claude.com":       "anthropic.com",
}

app = Flask(__name__)
CORS(app)


def _available_domains() -> list[str]:
    if not PLATFORMS_DIR.exists():
        return []
    return [p.stem for p in PLATFORMS_DIR.glob("*.json")]


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "platforms": _available_domains()})


@app.route("/api/site/<path:domain>", methods=["GET"])
def get_site(domain: str):
    domain = domain.lower().strip().removeprefix("www.")
    canonical = ALIASES.get(domain, domain)
    path = PLATFORMS_DIR / f"{canonical}.json"

    if not path.exists():
        return jsonify({
            "error": "not_found",
            "message": (
                f"Domain '{domain}' not in database. "
                f"Supported: {', '.join(SUPPORTED_DOMAINS)}"
            ),
        }), 404

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/concepts", methods=["GET"])
def get_concepts():
    if not MAPPING_PATH.exists():
        return jsonify({"error": "mapping not found"}), 500
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)

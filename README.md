# LEXIA — EU AI Act Rights Checker

LEXIA is a browser extension that checks websites for EU AI Act compliance and explains citizens' rights in plain language. It works like Creative Commons for AI regulation: three layers — machine-readable Knowledge Graph, LLM-powered extraction, and a human-readable popup — all linked by traceable references back to the actual legal text.

The extension reads a platform's Terms of Service, maps it against the EU AI Act (2024/1689) and GDPR (2016/679) using Azure OpenAI, and shows a traffic-light semaphore with per-right and per-risk cards. Every finding links to the exact AKN article paragraph in EUR-Lex. A child-friendly mode simplifies the language for younger users, with Lex the robot mascot guiding them through their rights.

## Architecture

```
Browser Extension (popup.html / popup.js)
        │  chrome.storage.local
        │
   background.js  ──── GET /api/site/{domain} ────▶  Flask API (port 5050)
                                                           │
                                          backend/data/platforms/{domain}.json
                                                           │
                                              run_pipeline.py
                                           ┌──────┴──────────────┐
                                     tos_scraper           tos_extractor
                                     (ToSDR API /           (Azure OpenAI
                                      web scrape)            gpt-4o)
                                           │                     │
                                    wikidata_client        concept_akn_mapping.json
                                    (SPARQL)                     │
                                                           kg_builder.py
                                                      (AKN XML → triples)
                                                           │
                                                  32024R1689.xml (AI Act)
                                                  32016R0679.xml (GDPR)
```

## Setup

### 1. Environment variables

```bash
export AZURE_OPENAI_ENDPOINT="https://<your-resource>.openai.azure.com/"
export AZURE_OPENAI_KEY="<your-api-key>"
```

### 2. Install dependencies (Python ≥ 3.11)

```bash
pip install -r requirements.txt
```

### 3. Pre-process the 5 platforms

```bash
python backend/run_pipeline.py
```

This scrapes ToS pages, calls Azure OpenAI, queries Wikidata, computes semaphore scores, and saves results to `backend/data/platforms/`.

### 4. Start the API server

```bash
python backend/api/app.py
```

API runs on `http://localhost:5050`. Endpoints:
- `GET /api/health` — lists available platforms
- `GET /api/site/<domain>` — returns compliance data
- `GET /api/concepts` — returns the full concept mapping

### 5. Load the extension in Chrome

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `extension/` folder

### 6. Load the extension in Safari

The extension uses Chrome Manifest V3, which Safari 16+ supports natively via the Safari Web Extension wrapper. A helper script is provided:

```bash
bash extension/convert_to_safari.sh
```

This requires Xcode installed. The script runs `xcrun safari-web-extension-converter`, which generates an Xcode project. Open it, build the Mac app, then enable the extension in **Safari → Settings → Extensions → LEXIA**.

## Pre-processed platforms

| Platform | Domain | Semaphore | Score | Rights | Risks detected |
|---|---|---|---|---|---|
| ChatGPT | openai.com | 🔴 red | 0 | 6 | 2 |
| X / Twitter | twitter.com | 🔴 red | 0 | 6 | 2 |
| Klarna | klarna.com | 🔴 red | 0 | 6 | 3 |
| Claude | anthropic.com | 🔴 red | 0 | 6 | 4 |
| Facebook | facebook.com | 🔴 red | 37 | 6 | 2 |

**Finding:** all five major AI platforms score red. None explicitly grant EU AI Act rights (right to explanation, human oversight, AI transparency, complaint) in their Terms of Service or Privacy Policy — the regulation is new and compliance transparency is still lacking.

*(Scores computed live from scraped privacy policies — re-run the pipeline to refresh.)*

## Ontology sources

| Ontology | URI | Use |
|---|---|---|
| AIRO | https://w3id.org/airo | Risk levels, high-risk system types |
| DPV EU-AIAct | https://w3id.org/dpv/legal/eu/aiact | System types, roles, compliance |
| DPV EU-Rights | https://w3id.org/dpv/legal/eu/rights | Fundamental rights (CFREU) |
| VAIR | https://w3id.org/vair | Risk vocabulary |
| PrOnto | https://w3id.org/pronto | Rights and obligations icons |

## Legal texts

- **EU AI Act** — Regulation (EU) 2024/1689, AKN: `32024R1689`
- **GDPR** — Regulation (EU) 2016/679, AKN: `32016R0679`

EUR-Lex base: `https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:`

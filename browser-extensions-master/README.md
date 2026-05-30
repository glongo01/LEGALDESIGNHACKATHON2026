# AI Act Checker

A browser extension that checks websites for EU AI Act compliance and tells you which rights you have as a user.

Built at the **BO 2026 Legal Design Hackathon**.

---

## What it does

When you visit a site in our database, the toolbar icon turns:

| Icon | Meaning |
|------|---------|
| 🔴 Red | Prohibited AI practice detected (Art. 5 AIA) |
| 🟡 Yellow | High-risk AI in use — verify your rights |
| 🟢 Green | Transparency obligations appear met |

Click the icon for a breakdown of findings — which rights are explicitly granted, which are missing, and whether any practices are outright banned under EU law.

---

## Install (development build)

```bash
# 1 — install dependencies
npm install

# 2 — build
npm run build

# 3 — load in Chrome
# Open chrome://extensions → enable Developer mode → Load unpacked → select dist/chrome/
```


## License

AGPL-3.0-or-later. See `LICENSE`.

---

## Attribution

This project is a fork of the [ToS;DR browser extension](https://github.com/tosdr/browser-extensions)
by the ToS;DR Team, licensed under AGPL-3.0.

Modifications made in 2026 for the BO 2026 Legal Design Hackathon:
- Replaced the ToS;DR API backend with a self-contained bundled database
- Replaced the A–E grade system with a red/yellow/green EU AI Act semaphore
- Added rights and prohibited-practice findings mapped to specific AIA articles
- Removed donation, settings, and curator features

# Malaysia National Carbon Registry (CCU Registry) — Prototype v1

Interactive, single-file HTML prototype of a national Carbon Credit Unit registry for Malaysia.
All names and figures are **sample data**; logins and payments are simulated.

**Open it:** `index.html` (published via GitHub Pages).

## What you can try

| Role | Flow |
| --- | --- |
| Visitor | Public registry: totals, filters, project list, latest retirements |
| Registry Administrator (NRES) | Dashboard & approval queue → KYC approval → project registration → CCU issuance (OTP, serials, buffer) → Article 6 authorisation & corresponding adjustment → VCS/GS lock → Carbon Levy policy (cap, international threshold) → expiry reminders |
| Account holder (Sample Cement Bhd) | Marketplace & FPX/DuitNow payment (delivery versus payment) → Carbon Levy offset with live 20% cap and international-threshold checks → retirement certificate |

Use **Switch role** in the top bar to move between the two consoles; actions in one show up in the other and on the public registry.

## Contents

- `index.html` — interactive prototype (no build step, no dependencies besides Google Fonts)
- `canvas/` — static screen designs (Design canvas source, `.dc.html`)
- `tests/walkthrough.py` — Playwright walkthrough of all three roles (32 checks)

## Run the walkthrough

```bash
pip install playwright && playwright install chromium
python tests/walkthrough.py
```

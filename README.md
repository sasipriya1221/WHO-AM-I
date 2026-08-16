# WHO AM I? — Know Your Happiness

A hackathon MVP for a self-discovery game where **AI finds the clues and the human finds the meaning**.

## Core journey
- **Portal** — a quiet, gender-neutral threshold into the experience rather than a product dashboard.
- **Mirror** — a reflection puzzle completes as low-pressure familiarity grows. Entertainment data is permanently excluded from DNA evidence.
- **Human DNA** — a consented empty-room/helix space where recurring clues produce contestable hypotheses.
- **Compass** — a cinematic road and horizon that uses only user-defined DNA to ask about a current life chapter. It never recommends a major decision.
- **Vault** — a private memory chamber where the user can inspect purpose boundaries and delete evidence; deletion recalculates patterns.

## Run locally
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload --port 8080
```

Open the app at http://127.0.0.1:8080

Open the deterministic three-minute judge path at http://127.0.0.1:8080/demo

Verify the backend health check at http://127.0.0.1:8080/health

Expected health response:
```json
{
  "status": "ok",
  "service": "who-am-i",
  "version": "0.2.0"
}
```

## Docker
```bash
docker compose up --build
```

Then open http://127.0.0.1:8080

## Test
```bash
cd backend
pytest -q
```

The regression suite covers API behavior, the complete judge journey, cinematic scene contracts, responsive/accessibility safeguards, and inference-aware deletion. CI also syntax-checks every frontend JavaScript bundle.

## Privacy invariant
> Data collected to entertain the user can personalize the experience, but can never be used to psychologically interpret the user.

## AI architecture
The current runnable MVP includes a deterministic local evidence engine so it works without external credentials. The service boundary is intentionally designed so an LLM/embedding provider can later replace language extraction while evidence thresholds, provenance, counter-evidence, user authority, and purpose permissions stay application-controlled.

## Hackathon scope
This repository implements the smallest end-to-end proof of Mirror → DNA → Compass rather than every future feature.

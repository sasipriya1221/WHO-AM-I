# WHO AM I? — Know Your Happiness

A hackathon MVP for a self-discovery game where **AI finds the clues and the human finds the meaning**.

## Core journey
- **Mirror** — low-pressure, interest-based familiarity. Entertainment data is permanently excluded from DNA evidence.
- **Happiness DNA** — consented experiences become evidence; recurring clues produce contestable hypotheses.
- **Compass** — uses only user-defined DNA to ask reflective questions about a current life chapter. It never recommends a major decision.
- **Vault** — lets the user inspect and delete evidence; deletion recalculates patterns.

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

## Privacy invariant
> Data collected to entertain the user can personalize the experience, but can never be used to psychologically interpret the user.

## AI architecture
The current runnable MVP includes a deterministic local evidence engine so it works without external credentials. The service boundary is intentionally designed so an LLM/embedding provider can later replace language extraction while evidence thresholds, provenance, counter-evidence, user authority, and purpose permissions stay application-controlled.

## Hackathon scope
This repository implements the smallest end-to-end proof of Mirror → DNA → Compass rather than every future feature.

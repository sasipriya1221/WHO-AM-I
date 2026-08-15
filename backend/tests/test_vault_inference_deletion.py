import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def _build_repeated_autonomy(client: TestClient):
    token = uuid.uuid4().hex
    user = client.post(
        "/api/v1/users/demo",
        json={"display_name": "Vault User", "email": f"vault-{token}@demo.local"},
    ).json()
    uid = user["id"]
    assert client.post(f"/api/v1/dna/{uid}/consent", json={"consent": True}).status_code == 200

    experiences = [
        ("empty_room", "Freedom and choice are close to me."),
        ("future_me", "I want control over my own choices in the future."),
        ("reflection", "I feel independent when I choose my own direction."),
    ]
    for kind, text in experiences:
        response = client.post(
            f"/api/v1/dna/{uid}/experiences",
            json={
                "experience_type": kind,
                "input_mode": "text",
                "response": {"reflection": text},
                "consent_for_analysis": True,
            },
        )
        assert response.status_code == 200

    patterns = client.get(f"/api/v1/dna/{uid}/patterns").json()
    autonomy = next(p for p in patterns if p["label"] == "autonomy")
    assert autonomy["status"] == "repeated"

    strands = client.get(f"/api/v1/dna/{uid}/strands").json()
    strand = next(s for s in strands if s["pattern_id"] == autonomy["id"])
    rename = client.post(
        f"/api/v1/dna/{uid}/strands/{strand['id']}/rename",
        json={"user_label": "Having control over my own choices"},
    )
    assert rename.status_code == 200
    return uid, autonomy, strand


def test_vault_deletion_weakens_pattern_but_preserves_user_definition():
    client = TestClient(app)
    uid, autonomy, strand = _build_repeated_autonomy(client)

    mapping = client.get(f"/api/v1/vault/{uid}/inference-map")
    assert mapping.status_code == 200
    body = mapping.json()
    dna = next(x for x in body["dna"] if x["pattern_id"] == autonomy["id"])
    assert dna["pattern_status"] == "repeated"
    assert dna["support_count"] == 3
    assert dna["ai_label"] == "autonomy"
    assert dna["user_label"] == "Having control over my own choices"
    assert dna["ownership_state"] == "user_defined"

    supporting = [
        e for e in body["self_discovery"]
        if any(a["pattern_id"] == autonomy["id"] and a["relationship"] == "support" for a in e["affects"])
    ]
    assert len(supporting) == 3
    evidence_id = supporting[0]["id"]

    preview = client.get(f"/api/v1/vault/{uid}/evidence/{evidence_id}/impact")
    assert preview.status_code == 200
    affected = preview.json()["affected_patterns"][0]
    assert affected["pattern_status"] == "repeated"
    assert affected["support_count"] == 3
    assert affected["user_label"] == "Having control over my own choices"

    deleted = client.delete(f"/api/v1/vault/{uid}/evidence/{evidence_id}/with-impact")
    assert deleted.status_code == 200
    change = deleted.json()["changes"][0]
    assert change["before"]["pattern_status"] == "repeated"
    assert change["after"]["pattern_status"] == "emerging"
    assert change["before"]["support_count"] == 3
    assert change["after"]["support_count"] == 2
    assert change["ownership_preserved"] is True
    assert change["after"]["ai_label"] == "autonomy"
    assert change["after"]["user_label"] == "Having control over my own choices"
    assert change["after"]["strand_status"] == "user_defined"

    refreshed = client.get(f"/api/v1/vault/{uid}/inference-map").json()
    dna_after = next(x for x in refreshed["dna"] if x["pattern_id"] == autonomy["id"])
    assert dna_after["pattern_status"] == "emerging"
    assert dna_after["user_label"] == "Having control over my own choices"


def test_vault_keeps_entertainment_outside_self_discovery_inference():
    client = TestClient(app)
    token = uuid.uuid4().hex
    user = client.post(
        "/api/v1/users/demo",
        json={"display_name": "Mirror Only", "email": f"mirror-{token}@demo.local"},
    ).json()
    uid = user["id"]
    interest = client.post(
        f"/api/v1/mirror/{uid}/interests",
        json={"category": "game", "name": "Angry Birds"},
    )
    assert interest.status_code == 200

    mapping = client.get(f"/api/v1/vault/{uid}/inference-map").json()
    assert mapping["entertainment"][0]["label"] == "Angry Birds"
    assert mapping["entertainment"][0]["dna_allowed"] is False
    assert mapping["self_discovery"] == []
    assert mapping["dna"] == []


def test_vault_frontend_contract_contains_preview_delete_and_before_after_states():
    root = Path(__file__).resolve().parents[2]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (root / "frontend" / "vault.js").read_text(encoding="utf-8")
    css = (root / "frontend" / "vault.css").read_text(encoding="utf-8")

    assert "/static/vault.js" in html
    assert "/static/vault.css" in html
    assert "/inference-map" in js
    assert "/impact" in js
    assert "/with-impact" in js
    assert "See impact" in js
    assert "Delete reflection & recalculate DNA" in js
    assert "BEFORE" in js and "AFTER" in js
    assert "Your definition stayed yours" in js
    assert "AI NOTICED" in js and "YOU DEFINED" in js
    assert ".state-change" in css
    assert ".vault-owner-trail" in css

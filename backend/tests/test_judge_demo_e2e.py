from fastapi.testclient import TestClient

from app.main import app


def test_judge_golden_path_end_to_end():
    client = TestClient(app)

    # 1. EXPERIENCE — deterministic seed creates independent consented clues.
    seeded = client.post("/api/v1/demo/seed")
    assert seeded.status_code == 200
    demo = seeded.json()
    uid = demo["user"]["id"]
    pattern_id = demo["pattern"]["id"]
    strand_id = demo["strand"]["id"]
    chapter_id = demo["chapter"]["id"]
    delete_id = demo["delete_candidate_evidence_id"]

    assert demo["sequence"] == [
        "experience",
        "dna_reveal",
        "challenge",
        "human_rename",
        "compass",
        "delete_evidence",
        "dna_weakens",
    ]
    assert len(demo["experiences"]) == 3
    assert demo["entertainment"]["label"] == "Game of Thrones"
    assert demo["entertainment"]["purpose"] == "entertainment"
    assert demo["entertainment"]["dna_allowed"] is False

    # 2. DNA — three independent experiences are enough for Repeated.
    patterns = client.get(f"/api/v1/dna/{uid}/patterns").json()
    autonomy = next(p for p in patterns if p["id"] == pattern_id)
    assert autonomy["label"] == "autonomy"
    assert autonomy["status"] == "repeated"
    assert autonomy["support"] == 3

    why = client.get(f"/api/v1/dna/{uid}/patterns/{pattern_id}/why")
    assert why.status_code == 200
    assert len(why.json()["supporting"]) == 3

    # 3. CHALLENGE — semantic retrieval exposes contradictory context.
    challenged = client.post(f"/api/v1/dna/{uid}/patterns/{pattern_id}/challenge")
    assert challenged.status_code == 200
    challenge = challenged.json()
    assert challenge["status"] == "questioned"
    assert challenge["contradicting"]
    assert "You decide" in challenge["message"]

    # 4. HUMAN RENAME — user's language outranks the AI label.
    user_label = "Having control over my own choices"
    renamed = client.post(
        f"/api/v1/dna/{uid}/strands/{strand_id}/rename",
        json={"user_label": user_label},
    )
    assert renamed.status_code == 200
    rename = renamed.json()
    assert rename["ai_label"] == "autonomy"
    assert rename["user_label"] == user_label
    assert rename["status"] == "user_defined"

    # 5. COMPASS — carries the user's wording, never a recommendation.
    reflected = client.post(
        f"/api/v1/compass/{uid}/reflect",
        json={"chapter_id": chapter_id, "strand_id": strand_id, "focus": {}},
    )
    assert reflected.status_code == 200
    reflection = reflected.json()
    assert reflection["ownership_state"] == "user_defined"
    assert reflection["ai_original_label"] == "autonomy"
    assert reflection["user_defined_label"] == user_label
    assert user_label in reflection["text"]
    assert "Placement" in reflection["text"]
    assert "recommend" not in reflection["text"].lower()

    # 6. DELETE — preview proves this exact reflection affects autonomy.
    impact = client.get(f"/api/v1/vault/{uid}/evidence/{delete_id}/impact")
    assert impact.status_code == 200
    affected = next(
        p for p in impact.json()["affected_patterns"] if p["pattern_id"] == pattern_id
    )
    assert affected["support_count"] == 3
    assert affected["user_label"] == user_label
    assert affected["ownership_state"] == "user_defined"

    deleted = client.delete(
        f"/api/v1/vault/{uid}/evidence/{delete_id}/with-impact"
    )
    assert deleted.status_code == 200
    change = next(
        c for c in deleted.json()["changes"] if c["pattern_id"] == pattern_id
    )

    # 7. DNA WEAKENS — inference changes, authorship does not.
    assert change["before"]["support_count"] == 3
    assert change["after"]["support_count"] == 2
    assert change["after"]["pattern_status"] == "emerging"
    assert change["after"]["ai_label"] == "autonomy"
    assert change["after"]["user_label"] == user_label
    assert change["after"]["strand_status"] == "user_defined"
    assert change["ownership_preserved"] is True

    # The deleted evidence is actually gone from the inference map.
    inference = client.get(f"/api/v1/vault/{uid}/inference-map").json()
    remaining_ids = {item["id"] for item in inference["self_discovery"]}
    assert delete_id not in remaining_ids
    dna = next(item for item in inference["dna"] if item["pattern_id"] == pattern_id)
    assert dna["support_count"] == 2
    assert dna["pattern_status"] == "emerging"
    assert dna["display_label"] == user_label

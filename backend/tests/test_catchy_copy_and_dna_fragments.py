from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[2]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
VAULT = (ROOT / "frontend" / "vault.js").read_text(encoding="utf-8")
DEMO = (ROOT / "frontend" / "demo.js").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_approved_emotional_product_language_leads_the_experience_and_readme():
    for source in (INDEX, README):
        assert "WHO AM I?" in source
        assert "Find Your Happiness. Find Your You." in source
        assert "Every moment leaves a clue. What do yours say about you?" in source
        assert "AI reflects. You decide." in source

    for phrase in [
        "Meet Yourself",
        "It starts with the little things.",
        "Follow the Clues",
        "Happiness rarely announces itself. It leaves traces.",
        "Prove yourself wrong",
        "Look Again",
        "Where Are You Going?",
        "Your road. Your answer.",
        "Your Story. Your Control.",
    ]:
        assert phrase in INDEX
        assert phrase in README

    assert "If this clue leaves your story, it leaves my understanding too." in INDEX
    assert "Your meaning was yours. Only my evidence changed." in INDEX + VAULT + DEMO
    assert "You're still becoming you. And that's kind of the point." in INDEX


def test_prove_yourself_wrong_copy_keeps_the_existing_challenge_endpoint():
    assert '<button id="challengeBtn" class="secondary" type="button">Prove yourself wrong</button>' in INDEX
    assert '<button id="demoChallengeBtn" type="button">Prove yourself wrong' in INDEX
    assert "/patterns/${currentPattern}/challenge" in APP
    assert "/patterns/${currentPattern}/challenge" in DEMO
    challenge_flow = APP.split("$('#challengeBtn').addEventListener", 1)[1].split(
        "$('#notMeBtn').addEventListener", 1
    )[0]
    assert challenge_flow.index("await refreshDNA()") < challenge_flow.index(
        "box.innerHTML=resultMarkup"
    )


def test_frontend_grows_fragments_before_rendering_thresholded_patterns():
    assert 'id="dnaHelix" class="helix-core"' in INDEX
    assert 'id="dnaFragmentLedger"' in INDEX
    assert 'id="dnaFragmentStatus" role="status" aria-live="polite"' in INDEX
    assert "function acceptedClueExperiences" in APP
    assert "function syncDnaFragments" in APP
    assert "item.experience_id" in APP
    assert "fragment-visible" in APP and ".fragment-visible" in STYLES
    assert "fragment-new" in APP and "dnaFragmentArrive" in STYLES
    for fragment_total in (4, 8, 12):
        assert f"{fragment_total} FRAGMENTS" in APP
    assert "dataset.clueCount=String(nextCount)" in APP
    assert "dataset.visibleFragments=String(visibleSegments)" in APP
    assert "4 fragments after clue 1, 8 after clue 2, and 12 after clue 3" in README

    refresh = APP.split("async function refreshDNA", 1)[1].split("async function openReveal", 1)[0]
    assert refresh.index("syncDnaFragments") < refresh.index("const surfaced")
    assert refresh.index("await new Promise") < refresh.index("$('#patterns').innerHTML")
    assert "patternStatus==='repeated'||patternStatus==='questioned'" in refresh
    assert "strand.status==='user_defined'" in refresh


def test_each_accepted_experience_adds_progress_data_without_weakening_repeated_gate():
    client = TestClient(app)
    user = client.post(
        "/api/v1/users/demo",
        json={"display_name": "Fragment User", "email": "fragment-user@demo.local"},
    ).json()
    uid = user["id"]
    assert client.post(f"/api/v1/dna/{uid}/consent", json={"consent": True}).status_code == 200

    clues = [
        ("empty_room", "Freedom and choice are close to me."),
        ("future_me", "I want control over my own choices in the future."),
        ("reflection", "I feel independent when I choose my own direction."),
    ]
    expected_statuses = ["emerging", "emerging", "repeated"]

    for accepted_count, ((experience_type, reflection), expected_status) in enumerate(
        zip(clues, expected_statuses), start=1
    ):
        created = client.post(
            f"/api/v1/dna/{uid}/experiences",
            json={
                "experience_type": experience_type,
                "input_mode": "text",
                "response": {"reflection": reflection},
                "consent_for_analysis": True,
            },
        )
        assert created.status_code == 200
        assert created.json()["evidence_created"] >= 1

        inference_map = client.get(f"/api/v1/vault/{uid}/inference-map").json()
        accepted_experiences = {
            item["experience_id"] for item in inference_map["self_discovery"]
        }
        assert len(accepted_experiences) == accepted_count

        patterns = client.get(f"/api/v1/dna/{uid}/patterns").json()
        autonomy = next(item for item in patterns if item["label"] == "autonomy")
        assert autonomy["status"] == expected_status
        if accepted_count < 3:
            assert autonomy["status"] != "repeated"

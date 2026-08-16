from pathlib import Path

import pytest

from tests.provider_spies import NO_PROVIDER_CALLS
from tests.security_helpers import (
    app_database_inference_snapshot,
    assert_no_inference_side_effects,
    create_demo_user,
    public_inference_snapshot,
)


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("category", "name", "title_fragment", "question_fragment"),
    [
        ("series", "Game of Thrones", "GOT", "House Stark"),
        ("game", "Angry Birds", "Angry Birds", "launch"),
        ("sport", "cricket", "Cricket", "runs"),
    ],
)
def test_saved_interest_returns_a_playful_entertainment_only_activity(
    client,
    provider_spy,
    category: str,
    name: str,
    title_fragment: str,
    question_fragment: str,
):
    user_id = create_demo_user(
        client,
        email=f"playful-{category}@demo.local",
    )
    before = app_database_inference_snapshot(user_id)

    saved = client.post(
        f"/api/v1/mirror/{user_id}/interests",
        json={"category": category, "name": name},
    )

    assert saved.status_code == 200
    assert saved.json()["purpose"] == "entertainment"
    assert saved.json()["dna_allowed"] is False
    activity = client.get(
        f"/api/v1/mirror/{user_id}/game",
        params={"interest_id": saved.json()["id"]},
    )
    assert activity.status_code == 200
    payload = activity.json()
    assert payload["interest_id"] == saved.json()["id"]
    assert payload["purpose"] == "entertainment"
    assert payload["dna_allowed"] is False
    assert payload["interaction"] in {"quiz", "mini_game", "playful_choice"}
    assert title_fragment.lower() in payload["title"].lower()
    assert question_fragment.lower() in payload["question"].lower()
    playful_copy = " ".join(
        [payload["title"], payload["question"], *payload.get("options", [])]
    ).lower()
    for forbidden in (
        "personality",
        "diagnosis",
        "what this says about you",
        "what this means about you",
    ):
        assert forbidden not in playful_copy

    assert_no_inference_side_effects(
        before,
        app_database_inference_snapshot(user_id),
    )
    public = public_inference_snapshot(client, user_id)
    assert public["entertainment"] == [
        {
            "id": saved.json()["id"],
            "label": name,
            "purpose": "entertainment",
            "dna_allowed": False,
        }
    ]
    assert public["self_discovery"] == []
    assert public["dna"] == []
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS


def test_playful_route_defaults_to_the_most_recently_saved_interest(client):
    user_id = create_demo_user(client, email="playful-latest@demo.local")
    first = client.post(
        f"/api/v1/mirror/{user_id}/interests",
        json={"category": "series", "name": "Game of Thrones"},
    ).json()
    latest = client.post(
        f"/api/v1/mirror/{user_id}/interests",
        json={"category": "sport", "name": "cricket"},
    ).json()

    current_activity = client.get(f"/api/v1/mirror/{user_id}/game")
    first_activity = client.get(
        f"/api/v1/mirror/{user_id}/game",
        params={"interest_id": first["id"]},
    )

    assert current_activity.status_code == 200
    assert current_activity.json()["interest_id"] == latest["id"]
    assert "cricket" in current_activity.json()["title"].lower()
    assert first_activity.status_code == 200
    assert first_activity.json()["interest_id"] == first["id"]
    assert "got" in first_activity.json()["title"].lower()


def test_frontend_requests_play_for_the_interest_that_was_just_saved():
    save_flow = APP.split("$('#interestForm').addEventListener", 1)[1].split(
        "async function loadGame", 1
    )[0]
    load_flow = APP.split("async function loadGame", 1)[1].split(
        "$('#loadGame').addEventListener", 1
    )[0]

    assert "const savedInterest=await api" in save_flow
    assert "await loadGame(savedInterest.id)" in save_flow
    assert "interest_id=${encodeURIComponent(interestId)}" in load_flow
    assert "game.purpose==='entertainment'" in load_flow
    assert "game.dna_allowed===false" in load_flow

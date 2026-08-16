import pytest

from app.database import SessionLocal
from app.models.entities import (
    DNAStrand,
    Pattern,
    PatternStatus,
    StrandStatus,
    User,
)
from tests.security_helpers import (
    app_database_inference_snapshot,
    assert_no_inference_side_effects,
)


pytestmark = pytest.mark.security

VALID_LABEL = "Having control over my own choices"
LABEL_CASE_NAMES = {
    "": "empty",
    " ": "one-space",
    "   ": "spaces",
    "\n\t ": "newline-tab",
    "\x00\x1f": "control-characters",
}


def _seed_strand(
    *,
    email: str,
    user_label: str | None = None,
    status: StrandStatus = StrandStatus.AI_PROPOSED,
) -> tuple[str, str]:
    with SessionLocal() as db:
        user = User(email=email, display_name="Rename Regression", dna_consent=True)
        db.add(user)
        db.flush()
        pattern = Pattern(
            user_id=user.id,
            ai_label="autonomy",
            description="Possible recurring clue around autonomy.",
            status=PatternStatus.EMERGING,
            support_count=1,
            contradiction_count=0,
        )
        db.add(pattern)
        db.flush()
        strand = DNAStrand(
            user_id=user.id,
            pattern_id=pattern.id,
            ai_original_label="autonomy",
            user_label=user_label,
            status=status,
        )
        db.add(strand)
        db.commit()
        return user.id, strand.id


def _assert_user_label_validation_error(response) -> None:
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"detail"}
    assert isinstance(body["detail"], list)
    # TODO(repository-specific): Lock the exact Pydantic error type/message after
    # the schema chooses its validator. The stable contract is the field location.
    assert any(
        detail.get("loc") == ["body", "user_label"]
        for detail in body["detail"]
    )


@pytest.mark.parametrize(
    ("method", "suffix"),
    [("post", "/rename"), ("patch", "")],
    ids=["canonical-post", "legacy-patch"],
)
@pytest.mark.parametrize(
    "user_label",
    ["", " ", "   ", "\n\t ", "\x00\x1f"],
    ids=["empty", "one-space", "spaces", "newline-tab", "control-characters"],
)
def test_rename_rejects_empty_or_whitespace_only_labels(
    client,
    method: str,
    suffix: str,
    user_label: str,
):
    user_id, strand_id = _seed_strand(
        email=f"rename-{method}-{LABEL_CASE_NAMES[user_label]}@demo.local"
    )
    before = app_database_inference_snapshot(user_id)

    response = getattr(client, method)(
        f"/api/v1/dna/{user_id}/strands/{strand_id}{suffix}",
        json={"user_label": user_label},
    )

    after = app_database_inference_snapshot(user_id)
    assert_no_inference_side_effects(before, after)
    _assert_user_label_validation_error(response)


def test_valid_user_rename_positive_control_is_saved_and_used_by_compass(client):
    user_id, strand_id = _seed_strand(email="rename-positive@demo.local")

    renamed = client.post(
        f"/api/v1/dna/{user_id}/strands/{strand_id}/rename",
        json={"user_label": VALID_LABEL},
    )

    assert renamed.status_code == 200
    assert renamed.json() == {
        "id": strand_id,
        "ai_label": "autonomy",
        "user_label": VALID_LABEL,
        "status": "user_defined",
    }
    chapter = client.post(
        f"/api/v1/compass/{user_id}/chapters",
        json={"title": "Placement"},
    )
    assert chapter.status_code == 200
    reflection = client.post(
        f"/api/v1/compass/{user_id}/reflect",
        json={"chapter_id": chapter.json()["id"], "strand_id": strand_id, "focus": {}},
    )
    assert reflection.status_code == 200
    assert reflection.json()["user_defined_label"] == VALID_LABEL
    assert VALID_LABEL in reflection.json()["text"]


def test_valid_user_rename_is_trimmed_before_storage(client):
    user_id, strand_id = _seed_strand(email="rename-trim@demo.local")
    before = app_database_inference_snapshot(user_id)

    response = client.post(
        f"/api/v1/dna/{user_id}/strands/{strand_id}/rename",
        json={"user_label": f"  {VALID_LABEL}  "},
    )

    assert response.status_code == 200
    assert response.json()["user_label"] == VALID_LABEL
    after = app_database_inference_snapshot(user_id)
    assert after.experiences == before.experiences
    assert after.evidence == before.evidence
    assert after.embedding_refs == before.embedding_refs
    assert after.graph_edges == before.graph_edges
    assert after.patterns == before.patterns
    assert len(after.dna_strands) == 1
    assert after.dna_strands[0][3:] == (VALID_LABEL, "user_defined")


def test_user_rename_rejects_labels_over_storage_limit(client):
    user_id, strand_id = _seed_strand(email="rename-too-long@demo.local")
    before = app_database_inference_snapshot(user_id)

    response = client.post(
        f"/api/v1/dna/{user_id}/strands/{strand_id}/rename",
        json={"user_label": "x" * 201},
    )

    _assert_user_label_validation_error(response)
    assert_no_inference_side_effects(before, app_database_inference_snapshot(user_id))


def test_compass_rejects_legacy_user_defined_strand_with_blank_label(client):
    user_id, strand_id = _seed_strand(
        email="rename-legacy-blank@demo.local",
        user_label=" \n\t ",
        status=StrandStatus.USER_DEFINED,
    )
    chapter = client.post(
        f"/api/v1/compass/{user_id}/chapters",
        json={"title": "Placement"},
    )
    assert chapter.status_code == 200

    response = client.post(
        f"/api/v1/compass/{user_id}/reflect",
        json={"chapter_id": chapter.json()["id"], "strand_id": strand_id, "focus": {}},
    )

    assert response.status_code == 409
    # TODO(repository-specific): No response contract exists for malformed legacy
    # user-defined strands. Preserve FastAPI's detail envelope and lock the exact
    # wording after the Compass guard is implemented.
    detail = response.json().get("detail", "").lower()
    assert "compass" in detail
    assert "label" in detail or "user-defined" in detail

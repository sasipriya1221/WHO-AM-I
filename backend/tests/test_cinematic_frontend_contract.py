from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[2]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
VAULT = (ROOT / "frontend" / "vault.js").read_text(encoding="utf-8")
DEMO = (ROOT / "frontend" / "demo.js").read_text(encoding="utf-8")
STYLES = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
VAULT_STYLES = (ROOT / "frontend" / "vault.css").read_text(encoding="utf-8")
DEMO_STYLES = (ROOT / "frontend" / "demo.css").read_text(encoding="utf-8")


class AccessibilityAuditParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.labels_for = set()
        self.form_controls = []
        self.buttons_without_type = []
        self.images_without_name = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.append(element_id)
        if tag == "label" and attributes.get("for"):
            self.labels_for.add(attributes["for"])
        if tag in {"input", "select", "textarea"}:
            self.form_controls.append(attributes)
        if tag == "button" and "type" not in attributes:
            self.buttons_without_type.append(attributes.get("id", "unnamed"))
        if attributes.get("role") == "img" and not attributes.get("aria-label"):
            self.images_without_name.append(attributes.get("id", "unnamed"))


def test_approved_cinematic_worlds_are_real_interface_scenes():
    assert 'id="portal" class="view portal-world active"' in INDEX
    assert "gender-neutral human silhouette" in INDEX

    assert INDEX.count('class="mirror-shard"') == 12
    assert 'id="mirrorProgress"' in INDEX
    assert "setMirrorStage(3)" in APP

    assert 'id="dnaRoomVisual" class="dna-room"' in INDEX
    assert 'class="helix-core"' in INDEX
    assert "is-questioned" in APP
    assert "is-human" in APP

    assert 'class="compass-sky"' in INDEX
    assert '<span class="road"><i></i></span>' in INDEX

    assert 'id="vaultDoor" class="vault-door"' in INDEX
    assert "memory-corridor" in VAULT
    assert "entertainment-drawer" in VAULT
    assert "dna-drawer" in VAULT


def test_judge_path_is_separate_but_complete():
    assert '<a class="judge-entry" href="/demo">' in INDEX
    journey_navigation = INDEX.split('<div class="journey-links">', 1)[1].split("</div>", 1)[0]
    assert 'data-view="demo"' not in journey_navigation

    assert len(demo_steps := demoSteps_from_source()) == 7
    assert demo_steps == [
        "Experience",
        "Happiness DNA",
        "Prove It Wrong",
        "Look Again",
        "Compass",
        "Vault",
        "DNA weakens",
    ]
    for scene in ("experience", "dna", "challenge", "rename", "compass", "delete", "weakens"):
        assert f"'{scene}'" in DEMO


def demoSteps_from_source():
    declaration = DEMO.split("const demoSteps=[", 1)[1].split("];", 1)[0]
    return [item.strip().strip("'") for item in declaration.split(",")]


def test_demo_route_serves_the_cinematic_experience_without_changing_apis():
    client = TestClient(app)
    root = client.get("/")
    demo = client.get("/demo")

    assert root.status_code == 200
    assert demo.status_code == 200
    assert demo.text == root.text
    assert "Watch the AI lose authority—on purpose." in demo.text
    assert "/demo" not in client.get("/openapi.json").json()["paths"]


def test_static_frontend_has_accessible_names_and_unambiguous_controls():
    parser = AccessibilityAuditParser()
    parser.feed(INDEX)

    duplicates = [element_id for element_id, count in Counter(parser.ids).items() if count > 1]
    assert duplicates == []
    assert parser.buttons_without_type == []
    assert parser.images_without_name == []

    unlabeled = [
        control.get("id", "unnamed")
        for control in parser.form_controls
        if control.get("id") not in parser.labels_for and not control.get("aria-label")
    ]
    assert unlabeled == []

    assert '<html lang="en">' in INDEX
    assert 'class="skip-link"' in INDEX
    assert 'role="status" aria-live="polite"' in INDEX
    assert "setAttribute('aria-hidden'" in APP
    assert "aria-current" in APP
    assert ":focus-visible" in STYLES
    assert "prefers-reduced-motion: reduce" in STYLES


def test_responsive_and_ownership_visual_contracts_are_ci_guarded():
    combined_css = STYLES + VAULT_STYLES + DEMO_STYLES
    assert combined_css.count("@media (max-width:") >= 8
    assert ".dna-chip.human" in STYLES
    assert ".reveal-panel.human-defined" in STYLES
    assert ".vault-dna-card.human-owned" in VAULT_STYLES
    assert ".ownership-demo .node.human" in DEMO_STYLES
    assert "border-style:solid" in DEMO_STYLES


def test_all_golden_path_frontend_calls_still_target_existing_api_contracts():
    source = APP + VAULT + DEMO
    required = [
        "/api/v1/demo/seed",
        "/patterns/${currentPattern}/why",
        "/patterns/${currentPattern}/challenge",
        "/strands/${currentStrand}/rename",
        "/compass/${userId}/reflect",
        "/evidence/${id}/impact",
        "/evidence/${id}/with-impact",
    ]
    for endpoint in required:
        assert endpoint in source

    assert "Your meaning was yours. Only my evidence changed." in source
    assert "No recommendation follows" in INDEX

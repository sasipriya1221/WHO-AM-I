from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")


def test_reveal_screen_exposes_all_contestable_controls():
    """The judge-facing Reveal must expose every human-authority action."""
    for control_id in ("whyBtn", "challengeBtn", "notMeBtn", "renameInput", "renameBtn"):
        assert f'id="{control_id}"' in INDEX

    assert "AI hypotheses are dotted. Your definitions are solid." in INDEX
    assert "AI noticed this. You decide what it means." in INDEX
    assert "The AI's words do not have to become yours." in INDEX


def test_reveal_javascript_calls_real_milestone2_endpoints():
    """The Reveal must be wired to backend state, not decorative UI."""
    assert "/why`" in APP
    assert "/challenge`" in APP
    assert "/not-me`" in APP
    assert "/rename`" in APP

    assert "method:'POST'" in APP
    assert "currentPattern" in APP
    assert "currentStrand" in APP


def test_reveal_preserves_ai_vs_user_ownership_states():
    """AI hypotheses and user-defined strands must remain visually distinct."""
    assert "AI hypothesis" in APP
    assert "Defined by you" in APP
    assert "human-defined" in APP
    assert "dna-chip" in STYLES
    assert ".dna-chip.human" in STYLES
    assert ".reveal-panel.human-defined" in STYLES


def test_challenge_copy_makes_counter_evidence_visible():
    assert "The AI tried to prove itself wrong." in APP
    assert "counter-evidence" in APP
    assert "semantic similarity" in APP


def test_rejection_and_rename_copy_preserve_human_authority():
    assert "It will not be treated as your identity or used by Compass." in APP
    assert "The AI's label did not become your identity. Your interpretation did." in APP
    assert "Defined by you. Mirror originally suggested" in APP

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "demo.js").read_text(encoding="utf-8")
CSS = (ROOT / "frontend" / "demo.css").read_text(encoding="utf-8")


def test_judge_demo_exposes_all_golden_path_steps():
    for text in [
        "Experience",
        "HAPPINESS DNA",
        "CHALLENGE",
        "HUMAN RENAME",
        "COMPASS",
        "VAULT",
        "DNA WEAKENS",
    ]:
        assert text in INDEX

    assert "AI NOTICED" in INDEX
    assert "YOU DEFINED" in INDEX
    assert "Your definition stayed yours" in INDEX
    assert "No recommendation follows" in INDEX


def test_judge_demo_uses_real_backend_endpoints():
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
        assert endpoint in JS


def test_judge_demo_visually_distinguishes_ai_and_human_ownership():
    assert "ownership-demo" in CSS
    assert ".node.human" in CSS
    assert "border-style:solid" in CSS
    assert "AI NOTICED" in JS
    assert "YOU DEFINED" in JS


def test_demo_is_loaded_after_core_frontend():
    assert '<script src="/static/app.js?v=cinematic-1"></script>' in INDEX
    assert '<script src="/static/vault.js?v=cinematic-1"></script>' in INDEX
    assert '<script src="/static/demo.js?v=cinematic-1"></script>' in INDEX
    assert INDEX.index("app.js") < INDEX.index("demo.js")

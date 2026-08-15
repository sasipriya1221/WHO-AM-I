from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def _build_challenged_strand(client: TestClient, email: str):
    user = client.post('/api/v1/users/demo', json={'display_name': 'Compass User', 'email': email}).json()
    uid = user['id']
    assert client.post(f'/api/v1/dna/{uid}/consent', json={'consent': True}).status_code == 200
    for kind, text in [
        ('empty_room', 'Freedom and choice are close to me.'),
        ('future_me', 'I want control over my own choices.'),
        ('reflection', 'I feel independent when I choose my own direction.'),
        ('reflection', 'I do not always want complete freedom; too many choices can overwhelm me.'),
    ]:
        response = client.post(
            f'/api/v1/dna/{uid}/experiences',
            json={'experience_type': kind, 'input_mode': 'text', 'response': {'reflection': text}, 'consent_for_analysis': True},
        )
        assert response.status_code == 200
    pattern = next(p for p in client.get(f'/api/v1/dna/{uid}/patterns').json() if p['label'] == 'autonomy')
    assert client.post(f"/api/v1/dna/{uid}/patterns/{pattern['id']}/challenge").status_code == 200
    strand = next(s for s in client.get(f'/api/v1/dna/{uid}/strands').json() if s['pattern_id'] == pattern['id'])
    return uid, pattern, strand


def test_blind_spot_allows_reflection_but_blocks_compass_until_user_defines():
    client = TestClient(app)
    uid, pattern, strand = _build_challenged_strand(client, 'blind-spot-guard@demo.local')

    blind = client.get(f"/api/v1/dna/{uid}/strands/{strand['id']}/blind-spot")
    assert blind.status_code == 200
    payload = blind.json()
    assert payload['ownership_state'] == 'ai_challenged'
    assert payload['can_enter_compass'] is False
    assert payload['ai_label'] == 'autonomy'
    assert 'define' in payload['bridge_text'].lower()

    chapter = client.post(f'/api/v1/compass/{uid}/chapters', json={'title': 'Placement'}).json()
    blocked = client.post(
        f'/api/v1/compass/{uid}/reflect',
        json={'chapter_id': chapter['id'], 'strand_id': strand['id'], 'focus': {}},
    )
    assert blocked.status_code == 409
    assert 'only uses strands defined by the user' in blocked.json()['detail'].lower()


def test_user_defined_blind_spot_hands_exact_strand_to_compass_without_advice():
    client = TestClient(app)
    uid, pattern, strand = _build_challenged_strand(client, 'blind-spot-handoff@demo.local')

    renamed = client.post(
        f"/api/v1/dna/{uid}/strands/{strand['id']}/rename",
        json={'user_label': 'Having control over my own choices'},
    )
    assert renamed.status_code == 200

    blind = client.get(f"/api/v1/dna/{uid}/strands/{strand['id']}/blind-spot").json()
    assert blind['ownership_state'] == 'user_defined'
    assert blind['ai_label'] == 'autonomy'
    assert blind['user_label'] == 'Having control over my own choices'
    assert blind['can_enter_compass'] is True
    assert 'your interpretation' in blind['bridge_text'].lower()

    chapter = client.post(
        f'/api/v1/compass/{uid}/chapters',
        json={'title': 'Placement', 'description': 'Applications and interview preparation are taking most of my attention.'},
    ).json()
    reflection = client.post(
        f'/api/v1/compass/{uid}/reflect',
        json={'chapter_id': chapter['id'], 'strand_id': strand['id'], 'focus': {}},
    )
    assert reflection.status_code == 200
    data = reflection.json()
    assert data['type'] == 'question'
    assert data['ownership_state'] == 'user_defined'
    assert data['ai_original_label'] == 'autonomy'
    assert data['user_defined_label'] == 'Having control over my own choices'
    assert data['chapter'] == 'Placement'
    assert 'trade-off intentional' in data['text']
    assert 'never recommends a decision' in data['note'].lower()
    forbidden = ['you should', 'choose ', 'recommend', 'best option']
    assert not any(term in data['text'].lower() for term in forbidden)


def test_frontend_contains_memorable_blind_spot_to_compass_ownership_flow():
    root = Path(__file__).resolve().parents[2]
    html = (root / 'frontend' / 'index.html').read_text(encoding='utf-8')
    js = (root / 'frontend' / 'app.js').read_text(encoding='utf-8')
    css = (root / 'frontend' / 'styles.css').read_text(encoding='utf-8')

    for control in ['blindSpotPanel', 'openBlindSpotBtn', 'toCompassBtn', 'compassHandoff', 'compassReflection']:
        assert f'id="{control}"' in html

    assert 'AI NOTICED' in html
    assert 'YOU DEFINED' in html
    assert 'No recommendation follows. The next move is yours.' in html
    assert '/blind-spot' in js
    assert 'strand_id:compassStrandId' in js
    assert "setView('compass')" in js
    assert "ownership_state" in js
    assert '.blind-spot' in css
    assert '.handoff-card' in css
    assert '.compass-silence' in css

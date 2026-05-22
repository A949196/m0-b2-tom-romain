"""Tests pytest pour POST /predict — Tâche 6 du brief M0-B2.

3 tests :
    1. Cas valide → 200 + structure de réponse SentimentOut OK
    2. Texte vide ou > 2000 caractères → 422
    3. Test paramétré sur 3 reviews du CSV → 200 + structure valide
"""
from __future__ import annotations

import csv

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Chemin vers le CSV de reviews fictives (monté en volume dans le conteneur)
CSV_PATH = "/app/data/sample_reviews.csv"


# ---------------------------------------------------------------------------
# Fixture client — with TestClient(app) déclenche le lifespan FastAPI
# (chargement du pipeline HF). Sans le `with`, pipeline reste None.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    """Client HTTP partagé pour toute la session de tests.

    `scope="session"` : le lifespan (et le chargement du modèle ~2-3 s)
    n'est exécuté qu'une seule fois pour l'ensemble des tests.
    """
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_sentiment_out(body: dict) -> None:
    """Vérifie la structure complète d'une réponse SentimentOut."""
    assert "sentiment" in body, "Champ 'sentiment' manquant"
    assert "scores_5_stars" in body, "Champ 'scores_5_stars' manquant"
    assert "model_name" in body, "Champ 'model_name' manquant"
    assert "latence_ms" in body, "Champ 'latence_ms' manquant"

    assert body["sentiment"] in {"négatif", "neutre", "positif"}, (
        f"Sentiment inattendu : {body['sentiment']!r}"
    )

    expected_keys = {"1 star", "2 stars", "3 stars", "4 stars", "5 stars"}
    assert set(body["scores_5_stars"].keys()) == expected_keys, (
        f"Clés scores_5_stars inattendues : {set(body['scores_5_stars'].keys())}"
    )
    for key, score in body["scores_5_stars"].items():
        assert isinstance(score, float), f"Score non-float pour {key!r}"
        assert 0.0 <= score <= 1.0, f"Score hors [0,1] pour {key!r} : {score}"

    assert isinstance(body["model_name"], str) and body["model_name"], (
        "model_name doit être une chaîne non vide"
    )
    assert isinstance(body["latence_ms"], (int, float)), "latence_ms doit être numérique"
    assert body["latence_ms"] >= 0, f"latence_ms négative : {body['latence_ms']}"


def _load_csv_reviews(n: int = 3) -> list[str]:
    """Charge les n premières reviews du CSV sample_reviews.csv."""
    reviews = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            texte = row.get("texte") or row.get("review") or row.get("text") or ""
            if texte.strip():
                reviews.append(texte.strip())
            if len(reviews) >= n:
                break
    return reviews


# ---------------------------------------------------------------------------
# Test 1 — Cas valide : 200 + structure SentimentOut complète
# ---------------------------------------------------------------------------

def test_predict_valid_returns_200_and_valid_structure(client) -> None:
    """POST /predict avec une review valide → 200 + SentimentOut conforme."""
    payload = {"texte": "La chambre était propre et le personnel très accueillant."}
    response = client.post("/predict", json=payload)

    assert response.status_code == 200, (
        f"Statut inattendu : {response.status_code} — {response.text}"
    )
    _assert_sentiment_out(response.json())


# ---------------------------------------------------------------------------
# Test 2 — Entrées invalides : 422
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "payload, description",
    [
        ({"texte": ""},          "texte vide"),
        ({"texte": "   "},       "texte composé uniquement d'espaces"),
        ({"texte": "a" * 2001},  "texte > 2000 caractères"),
        ({},                     "payload sans champ texte"),
    ],
)
def test_predict_invalid_input_returns_422(client, payload: dict, description: str) -> None:
    """POST /predict avec une entrée invalide → 422 sans planter le service."""
    response = client.post("/predict", json=payload)

    assert response.status_code == 422, (
        f"[{description}] Attendu 422, obtenu {response.status_code} — {response.text}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Paramétré sur 3 reviews du CSV : 200 + structure valide
# ---------------------------------------------------------------------------

def _csv_reviews_params() -> list[pytest.param]:
    """Charge 3 reviews du CSV pour la paramétrisation pytest."""
    try:
        reviews = _load_csv_reviews(n=3)
    except FileNotFoundError:
        pytest.skip(f"CSV introuvable : {CSV_PATH}", allow_module_level=True)
        return []

    return [
        pytest.param(review, id=f"review_{i+1}")
        for i, review in enumerate(reviews)
    ]


@pytest.mark.parametrize("texte", _csv_reviews_params())
def test_predict_csv_reviews_returns_200_and_valid_structure(client, texte: str) -> None:
    """POST /predict sur 3 reviews du CSV → 200 + SentimentOut conforme."""
    response = client.post("/predict", json={"texte": texte})

    assert response.status_code == 200, (
        f"Statut inattendu pour {texte[:50]!r}… : "
        f"{response.status_code} — {response.text}"
    )
    _assert_sentiment_out(response.json())
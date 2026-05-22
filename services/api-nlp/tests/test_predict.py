"""
Test de /predict
3 tests minimum : 
    (1) cas valide → 200 + structure réponse OK ;
    (2) texte vide ou > 2000 caractères → 422 ;
    (3) test paramétré sur 3 reviews du CSV.
Lancez docker compose exec api-nlp pytest -v
"""
from __future__ import annotations
from typing import Generator

from fastapi.testclient import TestClient

from app.main import app
import pytest

@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Fixture pour réutiliser le même TestClient (et donc le même pipeline) sur tous les tests."""
    with TestClient(app) as client:
        yield client

def test_predict_endpoint_valid() -> None:
    """Teste l'endpoint /predict avec un texte valide."""
    with TestClient(app) as client:
        response = client.post("/predict", json={"texte": "Excellente nuit, accueil au top, vue sur le bassin imprenable."})
    assert response.status_code == 200
    body = response.json()
    assert "sentiment" in body
    assert "scores_5_stars" in body
    assert body["sentiment"] in {"négatif", "neutre", "positif"}

def test_predict_endpoint_empty_text() -> None:
    """Teste l'endpoint /predict avec un texte vide."""
    with TestClient(app) as client:
        response = client.post("/predict", json={"texte": ""})
    assert response.status_code == 422

def test_predict_endpoint_long_text() -> None:
    """Teste l'endpoint /predict avec un texte > 2000 caractères."""
    long_text = "a" * 2001
    with TestClient(app) as client:
        response = client.post("/predict", json={"texte": long_text})
    assert response.status_code == 422 

def test_predict_endpoint_parametres() -> None:
    """Teste l'endpoint /predict avec plusieurs textes du CSV."""
    reviews = [
        "Personnel charmant, chambre impeccable, on reviendra !",
        "Hôtel bruyant, chambre sale, très déçu.",
        "Séjour correct, rien d'exceptionnel mais pas de gros problèmes non plus."
    ]
    with TestClient(app) as client:
        for review in reviews:
            response = client.post("/predict", json={"texte": review})
            assert response.status_code == 200
            body = response.json()
            assert "sentiment" in body
            assert body["sentiment"] in {"négatif", "neutre", "positif"}
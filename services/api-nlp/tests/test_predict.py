"""
Test de /predict
3 tests minimum : 
    (1) cas valide → 200 + structure réponse OK ;
    (2) texte vide ou > 2000 caractères → 422 ;
    (3) test paramétré sur 3 reviews du CSV.
Lancez docker compose exec api-nlp pytest -v
"""
from __future__ import annotations
import csv
from typing import Generator
from pathlib import Path

from fastapi.testclient import TestClient

from loguru import logger

from app.main import app
import pytest

@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Fixture pour réutiliser le même TestClient (et donc le même pipeline) sur tous les tests."""
    with TestClient(app) as client:
        yield client

def test_predict_endpoint_valid(client) -> None:
    """Teste l'endpoint /predict avec un texte valide."""
    #with TestClient(app) as client:
        #response = client.post("/predict", json={"texte": "Excellente nuit, accueil au top, vue sur le bassin imprenable."})
    response = client.post("/predict", json={"texte": "Excellente nuit, accueil au top, vue sur le bassin imprenable."})
    assert response.status_code == 200
    body = response.json()
    assert "sentiment" in body
    assert "scores_5_stars" in body
    assert body["sentiment"] in {"négatif", "neutre", "positif"}
    logger.info(f"Test texte valide, status code : {response.status_code}, response : {response.json()}")

def test_predict_endpoint_empty_text(client) -> None:
    """Teste l'endpoint /predict avec un texte vide."""
    #with TestClient(app) as client:
    response = client.post("/predict", json={"texte": ""})
    assert response.status_code == 422
    logger.warning(f"Test texte vide, status code : {response.status_code}, response : {response.json()}")

def test_predict_endpoint_long_text(client) -> None:
    """Teste l'endpoint /predict avec un texte > 2000 caractères."""
    long_text = "a" * 2001
    #with TestClient(app) as client:
    response = client.post("/predict", json={"texte": long_text})
    assert response.status_code == 422 
    logger.warning(f"Test texte long, status code : {response.status_code}, response : {response.json()}")

def test_predict_endpoint_parametres(client) -> None:
    """Teste l'endpoint /predict avec plusieurs textes du CSV."""
    # reviews = [
    #     "Personnel charmant, chambre impeccable, on reviendra !",
    #     "Hôtel bruyant, chambre sale, très déçu.",
    #     "Séjour correct, rien d'exceptionnel mais pas de gros problèmes non plus."
    # ]
    csv_file = Path("data") / "sample_reviews.csv"
    # TODO : MODEL_PATH = Path(__file__).resolve().parents[1] / "model" / "model.joblib"
    #print(f"Debug : path csv : {csv_file}")
    # récupérer le contenu du CSV avec le module csv pour respecter les guillemets
    with csv_file.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        reviews = [row for row in reader]
        #logger.info(f"Test paramétré, nombre de reviews chargées : {len(reviews)}, exemples : {reviews[:3]}")
    #reviews = csv_file.read_text(encoding="utf-8").splitlines()[1:8]  # on prend les 3 premières reviews (sans la ligne d'en-tête)
    #print(f"Debug : path reviews : {reviews}")
    #with TestClient(app) as client:
    for review in reviews:
        #print(f"Debug : review : {review}")
        response = client.post("/predict", json={"texte": review["texte"]})
        if review["sentiment_attendu"] != response.json().get("sentiment"):
            logger.warning(f"Sentiment prédictif inattendu : {response.json().get('sentiment')}, on attendait : {review['sentiment_attendu']} pour la review : {review['texte']}")
            #print(f"Debug : sentiment inattendu dans le CSV : {review['sentiment_attendu']}, on attendait : {response.json().get('sentiment')} pour la review : {review['texte']}")
        assert response.status_code == 200
        body = response.json()
        assert "sentiment" in body
        assert body["sentiment"] in {"négatif", "neutre", "positif"}

def test_predict_endpoint_parametres_mal_classees(client) -> None:
    csv_file = Path("data") / "bad_sample_reviews.csv"
    reviews = []
    with csv_file.open(encoding="utf-8") as f:
        header = f.readline().strip().split(",")  # lire la première ligne pour récupérer les noms de colonnes
        for line in f:
            values = line.strip().split(",")
            review_dict = dict(zip(header, values))  # créer un dictionnaire pour chaque ligne
            reviews.append(review_dict)
    #with TestClient(app) as client:
    for review in reviews:
        response = client.post("/predict", json={"texte": review["texte"]})
        #logger.info(f"Test review : {review['texte']}, sentiment attendu : {review['sentiment_attendu']}, sentiment prédit : {response.json().get('sentiment')}")   
        if review["sentiment_attendu"] != response.json().get("sentiment"):
            logger.warning(f"Sentiment prédictif inattendu : {response.json().get('sentiment')}, on attendait : {review['sentiment_attendu']} pour la review : {review['texte']}")
            #print(f"Debug : sentiment inattendu dans le CSV : {review['sentiment_attendu']}, on attendait : {response.json().get('sentiment')} pour la review : {review['texte']}")
        assert response.status_code == 200
        body = response.json()
        assert "sentiment" in body
        assert body["sentiment"] in {"négatif", "neutre", "positif"}
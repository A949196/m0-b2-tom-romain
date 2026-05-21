"""Logique d'inférence pour la classification de sentiment.

Le modèle CamemBERT chargé sort des labels 5 étoiles
(`'1 star'`, `'2 stars'`, ..., `'5 stars'`). Le métier (Aubergine Hôtels)
veut 3 classes (`négatif`, `neutre`, `positif`).

→ Ton travail dans ce fichier :
   1. Implémenter `predict_sentiment()` (récupère scores 5★ + appelle map).
   2. Implémenter `map_stars_to_sentiment()` (mapping 5★ → 3 classes).
   3. Justifier le seuil retenu en commentaire (cf. brief).

Le pipeline transformers est chargé une seule fois au démarrage, dans
`main.py` (lifespan), et stocké dans `state["pipeline"]`. Tu le récupères
en argument.
"""
from __future__ import annotations

import time
from typing import Any

from app.schemas import Sentiment, SentimentOut


def map_stars_to_sentiment(star_label: str) -> Sentiment:
    """Mappe un label 5 étoiles ('1 star', ..., '5 stars') en 3 classes métier.

    À compléter par l'apprenant. **Le choix du mapping est un arbitrage
    métier**, pas une recette imposée : plusieurs découpages sont valides
    (cf. mini-cours `02_HuggingFace_Transformers_essentiel.md`, section
    "Justification du seuil de mapping").

    Ton travail : proposer **ton** mapping et **le justifier** dans le
    README perso async (coût d'un faux positif / faux négatif côté
    métier Aubergine Hôtels).

    Args:
        star_label: label produit par le modèle (ex: '4 stars').

    Returns:
        Sentiment 3 classes.

    Raises:
        ValueError: si `star_label` n'est pas dans le format attendu.
    """
    nb = int(star_label[0])  # '4 stars' → 4
    if nb <= 2:
        return "négatif"
    if nb == 3:
        return "neutre"
    return "positif"


def predict_sentiment(pipeline: Any, text: str, model_name: str) -> SentimentOut:
    """Inférence de sentiment sur un texte FR.

    Args:
        pipeline: pipeline `transformers.pipeline("text-classification", ...)`
            chargé au démarrage de l'API.
        text: texte FR de la review.
        model_name: identifiant HF du modèle (passé pour traçabilité).

    Returns:
        SentimentOut avec sentiment 3 classes, scores 5★ bruts, et latence ms.
    """
    # TODO Tâche 3 — compléter :
    #
    # 1. Mesurer le temps d'inférence (time.perf_counter() avant/après).
    t0 = time.perf_counter()
    # 2. Appeler `pipeline(text, top_k=None)` pour récupérer toutes les
    #    probabilités (5 entrées, une par étoile).
    result = pipeline(text, top_k=None)
    #print(f"DEBUG result 2 type: {type(result)}, value: {result}", flush=True)
    # => 
    latence = (time.perf_counter() - t0) * 1000
    # 3. Construire `scores_5_stars: dict[str, float]` à partir du résultat.
    scores_5_stars = {item["label"]: item["score"] for item in result} #result[0]  # [{'label': '1 star', 'score': 0.04}, ..., {'label': '5 stars', 'score': 0.36}]
    #print(f"DEBUG scores_5_stars type: {type(scores_5_stars[0])}, value: {scores_5_stars[0]}", flush=True)
    # 4. Identifier le label argmax (la plus haute proba).
    argmax = max(result, key=lambda x: x["score"])["label"]
    # 5. Appeler `map_stars_to_sentiment(label_argmax)` pour obtenir la
    #    classe métier.
    sentiment = map_stars_to_sentiment(argmax)
    # 6. Renvoyer un `SentimentOut(...)`.
    return SentimentOut(
        sentiment=sentiment,
        scores_5_stars=scores_5_stars,
        model_name=model_name,
        latence_ms=latence
    )
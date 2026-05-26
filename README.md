# M0-B2 — Sentiment Analysis FR Aubergine Hôtels

## Architecture

````mermaid
---
config:
  layout: elk
---
flowchart TB
 subgraph Testing["Tests et données"]
        CSVReviews["reviews.csv<br>Jeu de test"]
        Pytest["pytest<br>Tests automatiques API"]
  end
 subgraph DockerNetwork["Réseau Docker interne"]
        StreamlitUI["Streamlit UI<br>Python<br>─ Champ texte review<br>─ Bouton « Analyser »"]
        FastAPI["FastAPI api-nlp<br>Python<br>─ /health / info / predict<br>─ Pydantic validation<br>─ Loguru → ./logs/api.log"]
        CamemBERT["CamemBERT FR<br>Sortie native : 5 étoiles<br>Cache HF → ./models"]
        Mapping["Mapping 5★ → 3 classes<br>Arbitrage métier"]
        Testing
  end
    QualityTeam["👤 Équipe qualité Aubergine<br>"] -- Navigateur Port 8501 --> StreamlitUI
    StreamlitUI -- httpx POST /predict (timeout 10 s) --> FastAPI
    FastAPI -- "transformers.pipeline" --> CamemBERT
    CamemBERT -- 5 étoiles --> Mapping
    Mapping --> SentimentResult["Sentiment FR<br>pour le métier"]
    Pytest -- Utilise --> CSVReviews
    Pytest -- Valide --> FastAPI

     CSVReviews:::test
     Pytest:::test
     StreamlitUI:::docker
     FastAPI:::docker
     CamemBERT:::docker
     Mapping:::docker
     QualityTeam:::team
     SentimentResult:::result
    classDef team fill:#f5f3ff,stroke:#a78bfa
    classDef docker fill:#ecfeff,stroke:#22d3ee
    classDef api fill:#fff7ed,stroke:#fb923c
    classDef ml fill:#f0fdf4,stroke:#4ade80
    classDef process fill:#fdf4ff,stroke:#e879f9
    classDef result fill:#fefce8,stroke:#facc15
    classDef test fill:#fff1f2,stroke:#fb7185
````

## Mise en service

Stack `docker compose` à 2 services qui démarre dès le clone (healthcheck
inclus).

```bash
# 1. Configurer l'environnement
cp .env.example .env

# 2. Construire et lancer la stack
docker compose up --build

# 3. Vérifier
curl http://localhost:8000/health        # API NLP
open  http://localhost:8501              # UI Streamlit
```

À l'arrêt : `Ctrl+C` puis `docker compose down` (les volumes `models/` et
`logs/` sont conservés — le modèle HF n'est pas re-téléchargé au prochain `up`).

> ⏱️ Le **1ᵉʳ démarrage** prend 3-5 min de build + 1-3 min de download du
> modèle CamemBERT (~270 Mo). Les démarrages suivants sont < 30 s grâce au
> cache volume `models/`.

---

## Modèle utilisé

**`cmarkea/distilcamembert-base-sentiment`** — DistilCamemBERT FR,
68 M paramètres, ~270 Mo.

⚠️ Le modèle sort **5 étoiles** (`'1 star'` … `'5 stars'`). Le métier
(Aubergine Hôtels) veut **3 classes** (`négatif/neutre/positif`).

→ Tu dois implémenter le **mapping 5★ → 3 classes** dans
`services/api-nlp/app/inference.py`. C'est le geste cœur de ce brief
(adaptation d'un service au format métier).

---

## Endpoints fournis

| Endpoint | Statut au clone | Ce que tu dois faire |
|---|---|---|
| `GET /health` | ✅ fonctionnel | rien |
| `GET /info` | ✅ fonctionnel | rien |
| `POST /predict` | ✅ fonctionnel | rien |

---

## Structure

```
.
├── docker-compose.yml             ← 2 services + healthcheck api-nlp
├── .env.example
├── services/
│   ├── api-nlp/                   ← FastAPI + transformers
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   │   ├── main.py            ← routes (lifespan + /health + /info + /predict)
│   │   │   ├── schemas.py         ← Pydantic ReviewIn / SentimentOut
│   │   │   └── inference.py       ← predict sentiment + mapping 5→3
│   │   └── tests/
│   │       └── test_health.py     ← 1 test pytest qui passe
│   │       └── test_predict.py     ← (1) cas valide → 200 + structure réponse OK ; (2) texte vide ou > 2000 caractères → 422 ; (3) test paramétré sur 3 reviews du CSV
│   └── ui-streamlit/              ← UI utilisateur
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app.py                 ← Bouton Analyser → appel POST /predict
├── data/
│   └── sample_reviews.csv         ← 30 reviews FR fictives (Aubergine Hôtels)
└── postman/
│   └── M0-B2_collection.json      ← à compléter
└── data/
    └── api.log                    ← Logger chaque requête /predict : texte tronqué à 80 caractères (RGPD-friendly), sentiment prédit, latence ms
```

---

## Healthcheck

Le `docker-compose.yml` inclut un `healthcheck` sur `api-nlp`. Au bout de
~40 s (le temps que le modèle se charge), le service passe `healthy`.
Vérification :

```bash
docker compose ps
# m0b2-api-nlp        Up X seconds (healthy)
```

Si le service reste `unhealthy` au bout de 2 min, regarde les logs :
`docker compose logs api-nlp`.

---

## Tests

Lance les tests **dans le conteneur API** :

```bash
docker compose exec api-nlp pytest -v
```

Au clone, 1 test passe (`test_health.py`). À toi d'ajouter au moins
2 tests pour `/predict`.

---

## Variables d'environnement (`.env`)

| Variable | Défaut | Usage |
|---|---|---|
| `MODEL_NAME_HF` | `cmarkea/distilcamembert-base-sentiment` | Modèle HF à charger |
| `MAX_TEXT_LENGTH` | `2000` | Validation Pydantic (longueur max texte) |

---

## Débugging rapide

| Symptôme | À tenter |
|---|---|
| `docker compose up` reste bloqué sur `pulling/building` | 1ᵉʳ build = 3-5 min + 1-3 min download modèle, patiente |
| `/predict` renvoie toujours 501 | Tu n'as pas encore complété `inference.py`, c'est normal |
| `/predict` renvoie `"1 star"` au lieu de `"négatif"` | Mapping 5→3 pas implémenté |
| L'UI affiche « API non branchée » | Tu dois compléter `app.py` dans `services/ui-streamlit/` |
| `Connection refused` depuis l'UI | Vérifie que l'URL est `http://api-nlp:8000` (nom de service docker), pas `localhost` |
| `ModuleNotFoundError` | Rebuild : `docker compose build --no-cache api-nlp` |
| Service `unhealthy` | `docker compose logs api-nlp` — le modèle ne se charge probablement pas (réseau, mémoire) |

Logs en temps réel : `docker compose logs -f api-nlp`.

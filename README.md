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

Stack Docker Compose à 2 services avec healthcheck intégré, pipeline de sentiment analysis et interface utilisateur.

```bash
# 1. Configurer l'environnement
cp .env.example .env

# 2. Construire et lancer la stack
docker compose up --build

# 3. Vérifier
curl http://localhost:8000/health        # API NLP (doit retourner 200)
open  http://localhost:8501              # UI Streamlit
```

À l'arrêt : `Ctrl+C` puis `docker compose down` (les volumes `models/` et
`logs/` sont conservés — le modèle HF n'est pas re-téléchargé au prochain `up`).

> ⏱️ Le **1ᵉʳ démarrage** prend 3-5 min de build + 1-3 min de download du
> modèle CamemBERT (~270 Mo). Les démarrages suivants sont < 30 s grâce au
> cache volume `models/`.

---

## 📦 **Stack technique**

| Service | Technologie | Port | Rôle |
| --- | --- | --- | --- |
| **API NLP** | FastAPI + Transformers | `8000` | Service d'inférence avec mapping 5→3 classes |
| **UI Streamlit** | Streamlit | `8501` | Interface utilisateur pour analyser les avis |
| **Modèle** | `cmarkea/distilcamembert-base-sentiment` | \- | DistilCamemBERT FR (68M paramètres) |
| **Logging** | Loguru | \- | Journalisation des requêtes avec rotation automatique |
| **Tests** | Pytest | \- | Validation de l'API et du mapping |

---

## 🔍 **Modèle utilisé**

[**`cmarkea/distilcamembert-base-sentiment`**](https://huggingface.co/cmarkea/distilcamembert-base-sentiment) — Modèle DistilCamemBERT spécialisé en sentiment analysis pour le français (68M paramètres, ~270 Mo).

**Adaptation métier** :
																   

- Le modèle original sort **5 classes** (`'1 star'`, `'2 stars'`, `'3 stars'`, `'4 stars'`, `'5 stars'`)
- **Mapping implémenté** dans `services/api-nlp/app/inference.py` :
    - **1-2 étoiles** → `négatif`
    - **3 étoiles** → `neutre`
    - **4-5 étoiles** → `positif`

> 💡 **Justification du mapping** : Ce découpage minimise les faux positifs pour les avis très négatifs (1-2 étoiles) tout en conservant une granularité suffisante pour l'analyse métier.

---

## 🔌 **Endpoints disponibles**

| Endpoint | Méthode | Statut | Description |
| --- | --- | --- | --- |
| `/health` | GET | ✅ | Vérification de la santé du service |
| `/info` | GET | ✅ | Métadonnées sur le modèle chargé |
| `/predict` | POST | ✅ | Analyse de sentiment avec mapping 5→3 classes |

**Exemple d'appel** :

```bash
curl --noproxy localhost -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"texte":"Personnel charmant, chambre impeccable…"}'
```

**Réponse attendue** :

```json
{
    "sentiment": "positif",
    "scores_5_stars": {
        "5 stars": 0.4574357271194458,
        "4 stars": 0.43361169099807739,
        "3 stars": 0.0919409990310669,
        "2 stars": 0.013017976656556129,
        "1 star": 0.0039935670793056488
    },
    "model_name": "cmarkea/distilcamembert-base-sentiment",
    "latence_ms": 488.63056400023197
}
```

---

## 🖼️ **Interface Utilisateur**

L'interface Streamlit permet une analyse interactive des avis :

<img width="1847" height="902" alt="UI Aubergine" src="https://github.com/user-attachments/assets/9c382957-ed4a-421e-9e59-31e13bb3a4c2" />

**Fonctionnalités** :

- Champ de texte pour saisir un avis
- Bouton "Analyser" déclenchant l'appel à l'API
- Affichage du sentiment avec couleur :
    - 🔴 Négatif
    - 🟠 Neutre
    - 🟢 Positif
- Affichage des scores 5 étoiles via un graphique à barres
- Gestion des erreurs (timeout 10s, API indisponible)

---

## 📊 **Fonctionnalités implémentées**

### 1\. **Mapping 5→3 classes**

- Implémentation robuste dans `services/api-nlp/app/inference.py`
- Gestion des erreurs pour les labels inattendus
- Justification du découpage dans le code

### 2\. **Journalisation avancée**

- Fichier `logs/api.log` avec :
    - Rotation automatique (5 Mo)
    - Rétention de 7 jours
    - Compression des logs anciens
- Champs enregistrés :
    - Texte tronqué (80 caractères pour respect RGPD)
    - Sentiment prédit
    - Latence de traitement

### 3\. **Tests automatisés**

- 4 tests dans `services/api-nlp/tests/test_predict.py` :
    - Cas valide → 200 + structure réponse OK
    - Texte vide → 422 (Unprocessable Entity)
    - Texte > 2000 caractères → 422
    - Tests paramétrés sur 3 avis du CSV `sample_reviews.csv`
	- Tests paramétrés sur des avis mal prédit du CSV `bad_sample_reviews.csv`

**Exécution des tests** :

```bash
docker compose exec api-nlp pytest -v
```

### 4\. **Intégration CI/CD**

- Healthcheck Docker vérifiant la disponibilité du modèle
- Vérification du format de réponse de l'API
- Tests exécutés automatiquement dans le conteneur

---

## 📁 **Structure du projet**

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
│   │       └── test_predict.py    ← (1) cas valide → 200 + structure réponse OK ; (2) texte vide ou > 2000 caractères → 422 ; (3) test paramétré sur 3 reviews du CSV
│   └── ui-streamlit/              ← UI utilisateur
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app.py                 ← Bouton Analyser → appel POST /predict
├── data/
│   ├── sample_reviews.csv         ← 30 reviews FR fictives (Aubergine Hôtels)
│   └── bad_sample_reviews.csv     ← 13 reviews FR fictives potentiellement mal classées (Aubergine Hôtels)
└── postman/
│   └── M0-B2_collection.json      ← Collection Postman
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

---

## Variables d'environnement (`.env`)

| Variable | Défaut | Usage |
|---|---|---|
| `MODEL_NAME_HF` | `cmarkea/distilcamembert-base-sentiment` | Modèle HF à charger |
| `MAX_TEXT_LENGTH` | `2000` | Validation Pydantic (longueur max texte) |

---

## 🛠 **Dépannage**

| Problème | Solution |
| --- | --- |
| `docker compose up` reste bloqué | 1er build = 3-5 min + 1-3 min download modèle |
| `/predict` retourne 501 | Vérifier que `inference.py` est bien complété |
| `/predict` retourne des labels 5 étoiles | Mapping 5→3 non implémenté ou erreur dans le code |
| UI affiche "API non branchée" | Vérifier l'URL dans `app.py` (`http://api-nlp:8000`) |
| `Connection refused` depuis l'UI | Utiliser le nom du service Docker (`api-nlp`) |
| Service `unhealthy` | `docker compose logs api-nlp` pour diagnostics |
| Logs volumineux | Vérifier la rotation dans `inference.py` |
| Tests échouent | Exécuter `docker compose exec api-nlp pytest -v` |

**Healthcheck** :

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

## 📖 **Documentation complémentaire**

- [Documentation du modèle](https://huggingface.co/cmarkea/distilcamembert-base-sentiment)
- [API FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Transformers Documentation](https://huggingface.co/docs/transformers/index)
- [Loguru Documentation](https://github.com/Delgan/loguru)

---

## 🤝 **Collaboration**

- **Pair programming** : Les rôles ont été switchés à mi-séance pour valider les deux parties (API et UI)
- **Commit** : Utilisation recommandée de `Co-authored-by` pour les commits en binôme
- **Branches** : Travailler sur des branches dédiées pour chaque fonctionnalité

---

## 🎯 **Bonnes pratiques**

1. **RGPD** : Les textes sont tronqués à 80 caractères dans les logs
2. **Performance** : Le modèle est chargé au démarrage (lifespan) pour éviter les latences
3. **Robustesse** :
    - Validation des entrées (Pydantic)
    - Gestion des erreurs (timeout, format invalide)
    - Tests couvrant les cas limites
4. **Maintenabilité** :
    - Code commenté et justifié
    - Tests automatisés
    - Documentation à jour

---

## 📌 **Points d'attention**

- **Ressources** : Le modèle nécessite ~270 Mo de RAM. Vérifier que Docker a assez de mémoire allouée.
- **Réseau** : Toujours utiliser le nom du service Docker (`api-nlp`) dans les appels internes, jamais `localhost`.
- **Volumes** : Les modèles téléchargés et logs sont conservés entre les redémarrages (`docker compose down` ne les supprime pas).

---

## 🔍 Analyses de reviews mal classées

Le modèle `cmarkea/distilcamembert-base-sentiment` présente des faiblesses potentielles sur certaines structures linguistiques. Exemples observés sur des reviews adversariales :

| Review | Attendu | Prédit | Explication |
|---|---|---|---|
| « Quel service client exceptionnel ! Ils ont mis 3 jours à répondre à notre demande d'oreiller supplémentaire. Bravo ! » | négatif | positif | **Ironie** non détectée : le modèle s'accroche aux mots positifs (`exceptionnel`, `Bravo`) sans saisir le contexte sarcastique. |
| « On ne peut pas dire que le petit-déjeuner manquait de quoi que ce soit. » | positif | négatif | **Double négation** mal résolue : le modèle compte les marqueurs négatifs (`pas`, `manquait`) sans appliquer ¬¬P = P. |
| « Moins pire que les avis ne le laissaient penser. » | neutre | négatif | **Comparatif** ignoré : le mot `pire` domine, l'atténuateur `moins` est sous-pondéré. |
| « Personnel catastrophique, accueil glacial, mais le petit-déjeuner était divin. » | négatif | positif | **Connecteur adversatif `mais`** : le modèle survalorise la seconde partie de la phrase et le superlatif `divin`. |
| « Conforme à mes attentes, ni plus ni moins. » | neutre | positif | **Classe neutre sous-représentée** dans le corpus d'entraînement → le modèle bascule vers la classe positive la plus proche. |

## 🎯 Justification du mapping 5★ → 3 classes

### Le mapping retenu

```python
MAPPING = {
    "1 star":  "négatif",
    "2 stars": "négatif",
    "3 stars": "neutre",
    "4 stars": "positif",
    "5 stars": "positif",
}
```

### Pourquoi ce choix ?

#### 1\. Alignement avec la sémantique originelle du modèle

Le modèle `cmarkea/distilcamembert-base-sentiment` a été entraîné sur des reviews Amazon/Allociné où **3 étoiles correspond historiquement à un avis mitigé** (« bof », « correct sans plus »). Préserver cette classe en `neutre` respecte la distribution apprise par le modèle et évite de forcer une polarité que le modèle lui-même n'a pas tranchée.

#### 2\. Symétrie et neutralité décisionnelle

Le mapping est **symétrique** : 2 classes côté négatif, 1 neutre, 2 classes côté positif. Cela évite d'introduire un **biais artificiel** vers une polarité (par exemple, mettre 3★ en négatif rendrait le système pessimiste : ~60 % des avis basculeraient en négatif sur un corpus hôtelier typique).

#### 3\. Cohérence avec le métier hôtelier

Pour Aubergine Hôtels, un client « neutre » correspond à un **signal d'amélioration** distinct des deux extrêmes :

| Classe | Action métier associée |
| --- | --- |
| **négatif** | 🚨 Alerte service client, réponse prioritaire, geste commercial |
| **neutre** | 📊 Analyse qualité, identifier les points d'amélioration silencieux |
| **positif** | 💬 Sollicitation pour avis public (Google, TripAdvisor), fidélisation |

Fusionner 3★ avec négatif ou positif **détruirait ce signal intermédiaire**, pourtant le plus précieux en amélioration continue (un client neutre ne se plaint pas mais ne reviendra pas non plus).

#### 4\. Coût d'erreur asymétrique : le critère décisif

En classification de sentiment, **toutes les erreurs n'ont pas le même coût métier**. C'est ce déséquilibre qui guide le choix final du mapping.

##### Matrice de coût (vue hôtelier)

| Réalité ↓ / Prédit → | Négatif | Neutre | Positif |
| --- | --- | --- | --- |
| **Négatif** (client mécontent) | ✅ OK | ⚠️ Coût modéré | 🔥 **Coût très élevé** |
| **Neutre** (client mitigé) | ⚠️ Coût faible | ✅ OK | ⚠️ Coût modéré |
| **Positif** (client satisfait) | ⚠️ Coût faible | ⚠️ Coût faible | ✅ OK |

##### Pourquoi le faux positif coûte plus cher que le faux négatif

- **Faux positif** (un client mécontent classé positif) :
    
    - Le système le **sollicite pour un avis public** → il poste un 1★ sur Google/TripAdvisor
    - Aucune action corrective n'est déclenchée → **perte de réputation durable**
    - Coût estimé : 1 avis négatif public ≈ **perte de 30 réservations futures** (étude Cornell, 2017)
- **Faux négatif** (un client satisfait classé négatif) :
    
    - Le système déclenche une alerte service client inutile → **coût opérationnel d'environ 5–10 minutes** de traitement
    - Pas d'impact réputationnel, voire un effet positif (« ils prennent soin de nous »)

➡️ **Le coût d'un faux positif est ~100× supérieur** à celui d'un faux négatif. Le mapping doit donc **favoriser le rappel côté négatif** (capter tous les mécontents, quitte à avoir des faux négatifs).

##### Comment le mapping retenu adresse ce déséquilibre

- En gardant **2★ dans `négatif`** (et non dans `neutre`), on garantit qu'un client modérément mécontent **n'est jamais classé positif**. Le pire scénario devient « 2★ → neutre » (erreur frontalière acceptable), pas « 2★ → positif » (catastrophe métier).
- En gardant **3★ en `neutre`**, on crée un **tampon protecteur** : un avis ambigu n'est jamais propulsé en `positif` sans confiance forte du modèle.


Ce choix devrait être revalidé après quelques semaines d'usage, idéalement avec une **matrice de confusion pondérée par les coûts métiers réels** (mesurés par l'équipe hôtelière).

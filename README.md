# 🧊 EatguAI — AI Fridge Assistant

> Snap a photo of your fridge. Get ranked recipes in seconds.

EatguAI combines **computer vision** and a **NLP-based recommendation engine** to detect ingredients from a fridge photo and suggest the best matching recipes — deployed as a production web app on Google Cloud Run.

---

## What makes it interesting

**The problem:** Traditional recipe apps require you to type ingredients manually. That's friction nobody wants.

**The solution:** Upload one photo → Gemini Vision identifies every ingredient → a TF-IDF recommender ranks 300 recipes by match score → you get step-by-step instructions in under 5 seconds.

**Key architectural decision:** Instead of training a custom YOLO model (explored and discarded due to dataset constraints and overfitting), we pivoted to zero-shot inference via Gemini 2.0 Flash. This eliminated the need for a labeled dataset, removed GPU dependency, and made the system generalizable to any real-world fridge photo.

---

## System Architecture

```
Photo → [Gemini 2.0 Flash / Vertex AI] → ingredient list
                                              ↓
                               [TF-IDF + Cosine Similarity]
                                              ↓
                               ranked recipes with match score
                                              ↓
                                    [Gradio UI / Cloud Run]
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Vision | Gemini 2.0 Flash via Vertex AI (zero-shot) |
| Recommendation | TF-IDF vectorization + Cosine Similarity (scikit-learn) |
| Scoring | Weighted ingredient matching + difficulty bonus per mode |
| Validation | Pydantic v2 |
| Interface | Gradio |
| Deployment | Docker → Google Artifact Registry → Cloud Run |

---

## Two Operating Modes

| Mode | Philosophy | Max missing ingredients |
|------|-----------|------------------------|
| 🧊 **Survival** | Cook strictly with what you have | 2 |
| 👨‍🍳 **Chef Pro** | Full gastronomic experience — techniques, pairings, plating | 5 |

Each mode has independent scoring weights, a distinct UI theme, and different recipe fields exposed.

---

## Dataset

300 Spanish recipes with structured fields: key ingredients (with quantities), base ingredients, step-by-step instructions, difficulty, cook time, calories, tags — plus Chef Pro fields (techniques, wine pairings, plating notes).

---

## Project Structure

```
eatguai/
├── app_gradiov4.py       → Entry point
├── config.py             → Centralized config (modes, colors, paths, Cloud vars)
├── models.py             → Pydantic v2 data models
│
├── core/
│   ├── vision.py         → Gemini Vision detection + ingredient normalization
│   └── recommender.py    → TF-IDF engine with weighted scoring
│
├── components/
│   ├── ui_renderer.py    → Dynamic HTML/CSS theming per mode
│   ├── detector.py       → Detection wrapper with error handling
│   └── analytics.py      → Session analytics dashboard
│
└── data/                 → Local only (not in repo)
    └── recetas_backend_proceso_ultra.json
```

---

## Deployment

The app runs on **Google Cloud Run** (serverless, auto-scaling). Deploy pipeline:

```bash
# 1. Clone
git clone https://github.com/catoralonso/eatguai.git && cd eatguai

# 2. Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p data
ENV PORT=8080
EXPOSE 8080
CMD ["python", "app_gradiov4.py"]
EOF

# 3. Set variables
export AR_REPO='eatguai'
export SERVICE_NAME='eatguai'
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_REGION='us-central1'

# 4. Create Artifact Registry repo
gcloud artifacts repositories create "$AR_REPO" \
  --location="$GOOGLE_CLOUD_REGION" --repository-format=Docker

# 5. Enable APIs
gcloud services enable aiplatform.googleapis.com run.googleapis.com

# 6. Build and push
gcloud builds submit \
  --tag "$GOOGLE_CLOUD_REGION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/$AR_REPO/$SERVICE_NAME"

# 7. Deploy
gcloud run deploy "$SERVICE_NAME" \
  --image "$GOOGLE_CLOUD_REGION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/$AR_REPO/$SERVICE_NAME" \
  --platform managed --region "$GOOGLE_CLOUD_REGION" \
  --allow-unauthenticated --memory 2Gi \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"
```

---

## Local Setup (Vertex AI Workbench)

```bash
git clone https://github.com/catoralonso/eatguai.git && cd eatguai
pip install -r requirements.txt
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
python app_gradiov4.py
```

---

## Version History

| Version | Highlights |
|---------|-----------|
| **v4** *(current)* | Modular architecture, dual modes, Pydantic v2, Cloud Run deployment, session analytics |
| v3 | Dark "Nevera de Noche" theme, recipe cards with match progress bar, user ratings |
| v2 | First working integration: vision + recommendations |

# 🧊 The Fridge Survival Guide

AI-powered fridge assistant that detects ingredients from a photo using Gemini Vision and recommends recipes using TF-IDF cosine similarity — built on Google Cloud Vertex AI.

## How it works

1. Upload a photo of your fridge
2. Gemini Vision detects all visible ingredients
3. The recommendation engine matches them against a database of 130+ recipes
4. Get ranked recipes with step-by-step instructions

## Tech Stack

- **Vision:** Google Gemini 2.0 Flash via Vertex AI
- **Recommendation:** TF-IDF + Cosine Similarity + Fuzzy Matching (scikit-learn)
- **Validation:** Pydantic v2
- **Interface:** Gradio
- **Cloud:** Google Cloud Vertex AI Workbench

## Setup

```bash
git clone https://github.com/catoralonso/The-Fridge-Survival-Guide.git
cd The-Fridge-Survival-Guide
pip install -r requirements.txt

# Set your Google Cloud project before running
export GOOGLE_CLOUD_PROJECT=your-project-id

python app_gradiov4.py
```

> **Note:** If running on a new Qwiklabs lab, just update the environment variable — no code changes needed.
> ```bash
> export GOOGLE_CLOUD_PROJECT=qwiklabs-gcp-xx-xxxxxxxxxx
> ```

## Project Structure

```
The-Fridge-Survival-Guide/
├── app_gradiov4.py          → Entry point unificado
├── config.py                → Configuración centralizada (colores, rutas, modos)
├── models.py                → Modelos Pydantic para validación de datos
├── requirements.txt
│
├── core/
│   ├── vision.py            → Detección de ingredientes con Gemini Vision
│   └── recommender.py       → Motor de recomendación TF-IDF + sustituciones
│
├── components/
│   ├── ui_renderer.py       → Renderizado HTML/CSS (tema Nevera de Noche)
│   ├── detector.py          → Wrapper de visión con manejo de errores
│   └── analytics.py         → Dashboard de sesión y persistencia
│
├── releases/                → Historial de versiones anteriores
│   ├── app_gradiov2.py
│   └── app_gradiov3.py
│
└── data/                    → Local only, no incluido en el repo
    └── recetas_backend_proceso_ultra.json
```

## Modes

| Mode | Description | Max missing ingredients |
|------|-------------|------------------------|
| 🧊 Survival | Cook with what you have right now | 2 |
| 👨‍🍳 Chef Pro | Full gastronomic experience with techniques and pairings | 5 |

## Version Log

### v4 — Pro Edition *(current)*
- Modular architecture: `core/` + `components/` separation
- Smart recommender: fuzzy matching + ingredient substitutions
- Pydantic v2 validation across all data layers
- Two modes: Survival and Chef Pro with dynamic UI
- Session analytics dashboard
- Centralized config with environment variable support
- Professional error handling with logging

### v3
- Improved interface, design and user experience
- Dark theme "Nevera de Noche"
- Expandable recipe cards with match progress bar
- User ratings saved to CSV

### v2
- Basic interface
- Ingredient detection from photo
- Recipe recommendations

## Dataset

130+ Spanish recipes stored in `recetas_backend_proceso_ultra.json` with the following fields per recipe: key ingredients with quantities, step-by-step instructions, difficulty, time, calories, tags, and Chef Pro fields (techniques, pairing, plating notes).

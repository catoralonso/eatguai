"""
Detección de ingredientes usando Gemini vía Vertex AI.
"""
import json
import logging
import unicodedata
from typing import List, Dict, Any

import vertexai
from vertexai.generative_models import GenerativeModel, Image as VertexImage

from config import CONFIG
from models import DetectedIngredient

logger = logging.getLogger(__name__)

# ============================================================================
# INICIALIZACIÓN VERTEX AI
# ============================================================================

vertexai.init(project=CONFIG.VERTEX_PROJECT_ID, location=CONFIG.VERTEX_LOCATION)
_model = GenerativeModel(CONFIG.GEMINI_MODEL)

# ============================================================================
# INGREDIENTES A DESCARTAR (del vision.py original)
# ============================================================================

DISCARD = {
    "ensalada de frutas", "ensalada de pasta", "mermelada de frutas",
    "aderezo para ensalada", "fiambre", "verduras de hoja", "hierbas",
    "aceite de cocina", "botella", "verdura", "comida",
    "bebida embotellada", "agua",
}

PROMPT = """
Mira esta imagen de una nevera y lista TODOS los ingredientes y productos visibles.
Devuelve ÚNICAMENTE un array JSON, sin ningún otro texto. Formato:
[
    {"name": "nombre del ingrediente", "confidence": 0.95},
    ...
]
Reglas:
- Usa nombres simples en ESPAÑOL (ej: "zanahoria" no "zanahoria fresca orgánica")
- Incluye todo lo visible: frutas, verduras, bebidas, condimentos, lácteos, sobras
- Confidence: 0.9 si se ve claramente, 0.7 si se ve parcialmente, 0.5 si hay incertidumbre
- NO incluyas nombres de marcas, pon el ingrediente real (ej: "zumo de naranja" no "Tropicana")
"""

# ============================================================================
# CATEGORÍAS
# ============================================================================

_CATEGORIES = {
    "lacteo":      ["leche", "queso", "yogur", "mantequilla", "crema", "nata"],
    "proteina":    ["pollo", "carne", "pescado", "atun", "huevo", "jamon", "tocino", "salmon"],
    "vegetal":     ["tomate", "lechuga", "cebolla", "ajo", "patata", "zanahoria", "pimiento", "espinaca"],
    "fruta":       ["manzana", "platano", "naranja", "limon", "fresa", "uva", "melocoton"],
    "grano":       ["arroz", "pasta", "pan", "harina", "avena", "legumbre", "lenteja", "garbanzo"],
    "condimento":  ["sal", "pimienta", "aceite", "vinagre", "salsa", "mostaza"],
}

def _infer_category(name: str) -> str:
    name_lower = name.lower()
    for cat, items in _CATEGORIES.items():
        if any(item in name_lower for item in items):
            return cat
    return "otro"

# ============================================================================
# NORMALIZACIÓN (del vision.py original)
# ============================================================================

def _normalize(name: str) -> str:
    n = name.lower().strip()
    n = unicodedata.normalize("NFD", n)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    if n.endswith("oes"):
        n = n[:-2]
    elif n.endswith("s") and not n.endswith("ss"):
        n = n[:-1]
    return n

# ============================================================================
# DETECCIÓN
# ============================================================================

class VisionError(Exception):
    pass

def detect_gemini(image_path: str) -> List[Dict[str, Any]]:
    """Envía la imagen a Gemini vía Vertex AI y devuelve lista raw."""
    try:
        image = VertexImage.load_from_file(image_path)
        response = _model.generate_content(
            [PROMPT, image],
            generation_config={"temperature": 0.1},
        )
        text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        logger.info(f"Gemini detectó {len(result)} ingredientes en bruto")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Gemini devolvió JSON inválido: {e}")
        raise VisionError(f"Respuesta de Gemini no es JSON válido: {e}")
    except Exception as e:
        logger.error(f"Error llamando a Vertex AI: {e}")
        raise VisionError(str(e))

# ============================================================================
# LIMPIEZA Y VALIDACIÓN
# ============================================================================

def clean_ingredients(
    raw: List[Dict[str, Any]],
    min_confidence: float = CONFIG.DEFAULT_CONFIDENCE,
) -> List[DetectedIngredient]:
    """Filtra, deduplica y valida ingredientes. Devuelve modelos Pydantic."""
    seen = set()
    cleaned = []

    for item in sorted(raw, key=lambda x: -float(x.get("confidence", 0))):
        try:
            conf = float(item.get("confidence", 0))
            name = item.get("name", "").strip()

            if not name or conf < min_confidence:
                continue

            name_norm = _normalize(name)

            if name_norm in DISCARD or name.lower() in DISCARD:
                continue

            if name_norm in seen:
                continue

            seen.add(name_norm)
            cleaned.append(DetectedIngredient(
                name=name,
                confidence=conf,
                raw_detection=str(item),
                category=_infer_category(name),
            ))
            logger.debug(f"  ✓ {name} ({conf:.0%}) [{_infer_category(name)}]")

        except Exception as e:
            logger.warning(f"Error procesando item {item}: {e}")
            continue

    logger.info(f"Ingredientes limpios: {len(cleaned)}")
    return cleaned

# ============================================================================
# FUNCIÓN PRINCIPAL (interfaz pública)
# ============================================================================

def detectar_ingredientes(image_path: str) -> List[DetectedIngredient]:
    """
    Función principal. Recibe path de imagen, devuelve lista de DetectedIngredient.
    Lanza VisionError si algo falla.
    """
    raw = detect_gemini(image_path)
    return clean_ingredients(raw)


# ============================================================================
# PRUEBA RÁPIDA
# ============================================================================

if __name__ == "__main__":
    import sys
    img = sys.argv[1] if len(sys.argv) > 1 else "foto_nevera.png"
    print(f"\n🔍 Analizando: {img}\n")
    ingredientes = detectar_ingredientes(img)
    print(f"INGREDIENTES DETECTADOS ({len(ingredientes)}):")
    for i in ingredientes:
        print(f"  {i.emoji} {i.name:<30} {i.confidence:.0%}  [{i.category}]")
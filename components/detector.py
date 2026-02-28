"""
Wrapper de detección con manejo de errores profesional.
components/detector.py
"""
import os
import logging
from typing import List
from PIL import Image

from config import CONFIG
from models import DetectedIngredient
from core.vision import detectar_ingredientes, VisionError

logger = logging.getLogger(__name__)


class GeminiDetectionError(Exception):
    pass


class NoIngredientsDetectedError(Exception):
    pass


class IngredientDetector:

    def __init__(self, min_confidence: float = CONFIG.DEFAULT_CONFIDENCE):
        self.min_confidence = min_confidence
        logger.info(f"IngredientDetector inicializado (confianza mínima: {min_confidence})")

    def detect(self, image_path: str) -> List[DetectedIngredient]:
        # 1. Verificar que el archivo existe
        if not os.path.exists(image_path):
            raise GeminiDetectionError(f"Imagen no encontrada: {image_path}")

        # 2. Validar que es una imagen legible y no es demasiado grande
        try:
            with Image.open(image_path) as img:
                w, h = img.size
                logger.debug(f"Imagen: {w}x{h} px, formato {img.format}")
                if w * h > 4_000_000:
                    logger.warning("Imagen >4MP, puede afectar al rendimiento")
        except Exception as e:
            raise GeminiDetectionError(f"No se puede leer la imagen: {e}")

        # 3. Llamar al módulo de visión real
        try:
            ingredientes = detectar_ingredientes(image_path)
        except VisionError as e:
            raise GeminiDetectionError(str(e))

        # 4. Filtrar por confianza mínima
        filtrados = [i for i in ingredientes if i.confidence >= self.min_confidence]

        if not ingredientes:
            raise NoIngredientsDetectedError("Gemini no detectó ningún ingrediente")

        if not filtrados:
            raise NoIngredientsDetectedError(
                f"Se detectaron {len(ingredientes)} items pero ninguno supera "
                f"la confianza mínima de {self.min_confidence:.0%}"
            )

        logger.info(f"Detección exitosa: {len(filtrados)} ingredientes válidos")
        return filtrados


def detect_with_fallback(
    image_path: str,
    min_conf: float = CONFIG.DEFAULT_CONFIDENCE,
) -> List[DetectedIngredient]:
    """
    Función de conveniencia para usar desde app_gradiov4.py.
    Nunca lanza excepción — devuelve lista vacía si algo falla,
    y loggea el error para diagnóstico.
    """
    try:
        return IngredientDetector(min_confidence=min_conf).detect(image_path)
    except NoIngredientsDetectedError as e:
        logger.warning(f"Sin ingredientes detectados: {e}")
        return []
    except GeminiDetectionError as e:
        logger.error(f"Fallo de detección: {e}")
        return []
        raise
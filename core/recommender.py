"""
Sistema de recomendación de recetas.
"""
import json
import logging
import unicodedata
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import CONFIG
from models import Recipe, RecipeIngredient, Recommendation

logger = logging.getLogger(__name__)


class RecommenderError(Exception):
    pass


# ============================================================================
# NORMALIZACIÓN
# ============================================================================

def _normalize(text: str) -> str:
    n = text.lower().strip()
    n = unicodedata.normalize("NFD", n)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    if n.endswith("oes"):
        n = n[:-2]
    elif n.endswith("s") and not n.endswith("ss"):
        n = n[:-1]
    return n


# ============================================================================
# SUSTITUCIONES
# ============================================================================

SUSTITUCIONES: Dict[str, List[str]] = {
    # Lácteos
    "nata":              ["crema de leche", "leche evaporada", "yogur griego"],
    "leche":             ["bebida de avena", "bebida de soja", "bebida de almendra"],
    "mantequilla":       ["aceite", "margarina", "aceite de coco"],
    "queso":             ["queso fresco", "requesón", "ricotta"],
    "nata agria":        ["yogur natural", "crema de leche con limon"],
    "queso crema":       ["yogur griego", "requesón"],
    "yogur":             ["kefir", "nata agria", "leche con limon"],

    # Proteínas
    "huevo":             ["aquafaba", "platano maduro", "semillas de chia con agua"],
    "carne picada":      ["soja texturizada", "lenteja cocida", "tofu desmenuzado"],
    "pollo":             ["pavo", "conejo", "tofu firme"],
    "carne de cerdo":    ["pollo", "pavo", "seitán"],
    "bacalao":           ["merluza", "pescadilla", "cualquier pescado blanco"],
    "atun lata":         ["sardinillas", "caballa en lata", "salmon ahumado"],
    "jamon":             ["pavo en lonchas", "bacon", "cecina"],

    # Aromáticos y condimentos
    "ajo":               ["ajo en polvo", "cebollino", "asafetida"],
    "cebolla":           ["puerro", "cebolleta", "cebolla en polvo"],
    "tomate frito":      ["tomate natural triturado", "tomate concentrado", "sofrito"],
    "limon":             ["vinagre de manzana", "lima", "naranja"],
    "vino blanco":       ["caldo de pollo", "zumo de limon", "vinagre blanco diluido"],
    "vino tinto":        ["caldo de carne", "zumo de uva", "vinagre tinto diluido"],
    "salsa de soja":     ["tamari", "aminoacidos de coco", "worcestershire"],

    # Harinas y espesantes
    "harina de trigo":   ["harina universal", "harina de maiz", "harina de arroz"],
    "pan rallado":       ["avena molida", "crackers triturados", "harina de maiz"],
    "maicena":           ["fecula de patata", "arrurruz", "harina de arroz"],

    # Endulzantes
    "azucar":            ["miel", "jarabe de agave", "azucar de coco"],
    "miel":              ["azucar", "jarabe de arce", "melaza"],

    # Verduras
    "patata":            ["boniato", "nabo", "colinabo"],
    "calabacin":         ["pepino", "calabaza", "berenjena"],
    "pimiento rojo":     ["pimiento amarillo", "tomate", "zanahoria asada"],
    "espinaca":          ["acelga", "col rizada", "canónigos"],
    "caldo de pollo":    ["agua con pastilla de caldo", "caldo vegetal", "agua con miso"],
    "caldo de carne":    ["agua con pastilla", "caldo de pollo", "agua con soja"],

    # Extras
    "pan":               ["tortilla de trigo", "pan de molde", "baguette"],
    "arroz":             ["quinoa", "cuscus", "bulgur"],
    "pasta":             ["espirales", "macarrones", "fideos"],
    "aceite de oliva":   ["aceite de girasol", "aceite de coco"],
}


def _has_sustitucion(needed: str, available_set: set) -> bool:
    """Comprueba si hay algún sustituto disponible para un ingrediente."""
    needed_norm = _normalize(needed)
    for sust in SUSTITUCIONES.get(needed_norm, []):
        if _normalize(sust) in available_set:
            return True
    return False

# ============================================================================
# DETECCIÓN DE RECETAS GENÉRICAS
# ============================================================================

MARCADORES_GENERICOS = [
    "segun el tipo de receta",
    "cocinar o mezclar los ingredientes",
    "preparar y mezclar los ingredientes principales",
    "añadir ingredientes base y ajustar sal",
]


def _tiene_proceso_real(proceso_detallado: List[str]) -> bool:
    """Devuelve True si el proceso tiene pasos reales, no texto de plantilla."""
    if not proceso_detallado or len(proceso_detallado) < 3:
        return False
    texto = " ".join(proceso_detallado).lower()
    return not any(m in texto for m in MARCADORES_GENERICOS)


# ============================================================================
# CLASE PRINCIPAL
# ============================================================================

class RecipeRecommender:

    def __init__(self, recipes_path: str = None):
        self.recipes_path = recipes_path or CONFIG.RECIPES_FILE
        self.recipes: List[Recipe] = []
        self.vectorizer = None
        self.tfidf_matrix = None

        self._load_recipes()
        self._init_vectorizer()
        logger.info(f"Recommender listo con {len(self.recipes)} recetas")

    # ── Carga ────────────────────────────────────────────────────────────────

    def _load_recipes(self):
        try:
            with open(self.recipes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_list = data if isinstance(data, list) else data.get("recetas", [])
            self.recipes = [self._adapt_recipe(r) for r in raw_list]
        except Exception as e:
            logger.error(f"Error cargando recetas: {e}")
            raise RecommenderError(f"No se pudieron cargar recetas: {e}")

    def _adapt_recipe(self, raw: Dict) -> Recipe:
        ingredientes = []
        for ing in raw.get("ingredientes_clave", []):
            if isinstance(ing, dict):
                ingredientes.append(RecipeIngredient.model_validate(ing))
            else:
                ingredientes.append(RecipeIngredient(item=str(ing)))

        proceso_det = raw.get("proceso_detallado", [])
        return Recipe(
            receta_id=raw.get("receta_id"),
            nombre=raw.get("nombre", "Sin nombre"),
            categoria=raw.get("categoria"),
            tipo=raw.get("tipo"),
            tags=raw.get("tags", []),
            ingredientes_clave=ingredientes,
            ingredientes_base=raw.get("ingredientes_base", []),
            proceso_corto=raw.get("proceso_corto"),
            proceso_detallado=proceso_det,
            tiempo_min=raw.get("tiempo_min"),
            dificultad=raw.get("dificultad"),
            calorias_aprox=raw.get("calorias_aprox"),
            tecnicas=raw.get("tecnicas", []),
            maridaje=raw.get("maridaje"),
            presentacion=raw.get("presentacion"),
            chef_notes=raw.get("chef_notes"),
            proceso_real=_tiene_proceso_real(proceso_det),
        )

    # ── TF-IDF ───────────────────────────────────────────────────────────────

    def _init_vectorizer(self):
        corpus = []
        for r in self.recipes:
            claves = " ".join(_normalize(i.item) for i in r.ingredientes_clave)
            nombre = _normalize(r.nombre)
            tags   = " ".join(r.tags).lower()
            base   = " ".join(r.ingredientes_base).lower()
            corpus.append(f"{nombre} {claves} {tags} {base}")

        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    # ── Match ────────────────────────────────────────────────────────────────

    def _ingredient_match(self, needed: str, available_set: set) -> bool:
        """Match flexible: exacto → contenido → fuzzy."""
        needed_norm = _normalize(needed)
        if needed_norm in available_set:
            return True
        for avail in available_set:
            if needed_norm in avail or avail in needed_norm:
                return True
            if SequenceMatcher(None, needed_norm, avail).ratio() > 0.8:
                return True
        return False

    def _calculate_match(
        self,
        recipe: Recipe,
        available_set: set,
    ) -> Tuple[List[str], List[RecipeIngredient]]:
        found, missing = [], []
        for ing in recipe.ingredientes_clave:
            if self._ingredient_match(ing.item, available_set):
                found.append(ing.item)
            elif _has_sustitucion(ing.item, available_set):
                found.append(f"{ing.item} (sustituible)")
            else:
                missing.append(ing)
        return found, missing

    # ── Filtros ──────────────────────────────────────────────────────────────

    def _apply_filtros(
        self,
        results: List[Recommendation],
        filtros: Optional[Dict],
    ) -> List[Recommendation]:
        if not filtros:
            return results

        if "max_tiempo" in filtros and filtros["max_tiempo"]:
            results = [
                r for r in results
                if (r.receta.tiempo_min or 999) <= filtros["max_tiempo"]
            ]

        if "max_faltantes" in filtros and filtros["max_faltantes"] is not None:
            results = [
                r for r in results
                if len(r.ingredientes_faltantes) <= filtros["max_faltantes"]
            ]

        return results

    # ── Recomendación principal ──────────────────────────────────────────────

    def recommend(
        self,
        ingredients: List[str],
        n: int = CONFIG.DEFAULT_N_RECIPES,
        modo: str = "survival",
        filtros: Optional[Dict] = None,
    ) -> List[Recommendation]:
        """
        Scoring en cascada:
          1. n_coincidencias absolutas
          2. porcentaje de receta cubierta
          3. TF-IDF como desempate
        En modo survival filtra recetas con más de 2 faltantes.
        """
        available_set = {_normalize(i) for i in ingredients}
        query_vec     = self.vectorizer.transform([" ".join(available_set)])
        similarities  = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        results = []
        for idx, recipe in enumerate(self.recipes):
            found, missing = self._calculate_match(recipe, available_set)
            n_found = len(found)

            if n_found == 0:
                continue

            total     = len(recipe.ingredientes_clave)
            match_pct = n_found / total if total > 0 else 0

            # Modo survival: máximo 2 faltantes
            if modo == "survival" and len(missing) > CONFIG.get_mode(modo)["max_missing"]:
                continue

            n_base_found = sum(1 for b in recipe.ingredientes_base if _normalize(b) in available_set)
            score_total = (n_found * 1000) + (n_base_found * 50) + (match_pct * 100) + float(similarities[idx])

            # Bonus por calidad: recetas con proceso real se muestran primero
            if recipe.proceso_real:
                score_total += 50
            # Bonus/penalización por dificultad según modo
            dificultad_bonus = CONFIG.get_mode(modo).get("dificultad_bonus", {})
            score_total += dificultad_bonus.get(recipe.dificultad or "media", 0)

            results.append(Recommendation(
                receta=recipe,
                porcentaje_match=match_pct,
                coincidencias=found,
                ingredientes_faltantes=missing,
                score_total=score_total,
            ))

        results.sort(key=lambda x: x.score_total, reverse=True)
        results = self._apply_filtros(results, filtros)

        logger.info(f"Recomendadas {min(n, len(results))} de {len(results)} candidatas")
        return results[:n]

    # ── Sustituciones para UI ────────────────────────────────────────────────

    def get_sustituciones(
        self,
        rec: Recommendation,
        available: List[str],
    ) -> List[Tuple[str, str]]:
        """
        Devuelve pares (ingrediente_faltante, sustituto_disponible).
        Para mostrar en la tarjeta de receta.
        """
        available_set = {_normalize(i) for i in available}
        suggestions = []
        for faltante in rec.ingredientes_faltantes:
            needed_norm = _normalize(faltante.item)
            for sust in SUSTITUCIONES.get(needed_norm, []):
                if _normalize(sust) in available_set:
                    suggestions.append((faltante.item, sust))
                    break
        return suggestions

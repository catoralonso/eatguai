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
    "nata":            ["crema de leche", "leche evaporada"],
    "vino blanco":     ["caldo de pollo", "zumo de limon"],
    "harina de trigo": ["harina universal", "harina de maiz"],
    "mantequilla":     ["aceite", "margarina"],
    "azucar":          ["miel", "jarabe de maiz"],
    "leche":           ["bebida de avena", "bebida de soja"],
}


def _has_sustitucion(needed: str, available_set: set) -> bool:
    """Comprueba si hay algún sustituto disponible para un ingrediente."""
    needed_norm = _normalize(needed)
    for sust in SUSTITUCIONES.get(needed_norm, []):
        if _normalize(sust) in available_set:
            return True
    return False


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

        return Recipe(
            receta_id=raw.get("receta_id"),
            nombre=raw.get("nombre", "Sin nombre"),
            categoria=raw.get("categoria"),
            tipo=raw.get("tipo"),
            tags=raw.get("tags", []),
            ingredientes_clave=ingredientes,
            ingredientes_base=raw.get("ingredientes_base", []),
            proceso_corto=raw.get("proceso_corto"),
            proceso_detallado=raw.get("proceso_detallado", []),
            tiempo_min=raw.get("tiempo_min"),
            dificultad=raw.get("dificultad"),
            calorias_aprox=raw.get("calorias_aprox"),
            tecnicas=raw.get("tecnicas", []),
            maridaje=raw.get("maridaje"),
            presentacion=raw.get("presentacion"),
            chef_notes=raw.get("chef_notes"),
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
            if modo == "survival" and len(missing) > CONFIG.get_mode("survival")["max_missing"]:
                continue

            score_total = n_found * 1000 + match_pct * 100 + float(similarities[idx])

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
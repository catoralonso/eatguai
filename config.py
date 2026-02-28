"""
Configuración centralizada de Fridge Survival Guide.
Colores, umbrales y comportamiento.
"""
from dataclasses import dataclass, field
from typing import Dict
import os

# ============================================================================
# PALETA DE COLORES - Nevera de Noche
# ============================================================================
@dataclass(frozen=True)
class Colors:
    """Paleta inspirada en hielo, neón suave y oscuridad profunda."""

    # Fondos
    BG_PRIMARY:    str = "#0a0a0f"
    BG_SECONDARY:  str = "#13131f"
    BG_TERTIARY:   str = "#0f0f1a"

    # Acentos
    ICE_BLUE:      str = "#7dd3fc"
    ICE_GLOW:      str = "rgba(125, 211, 252, 0.15)"
    PURPLE_NEBULA: str = "#a78bfa"
    TEAL_AURORA:   str = "#14b8a6"

    # Estados
    SUCCESS: str = "#34d399"
    WARNING: str = "#fbbf24"
    ERROR:   str = "#f87171"
    INFO:    str = "#60a5fa"

    # Texto
    TEXT_PRIMARY:   str = "#f8fafc"
    TEXT_SECONDARY: str = "#94a3b8"
    TEXT_MUTED:     str = "#64748b"

    # Bordes y efectos
    BORDER_GLOW:   str = "rgba(125, 211, 252, 0.25)"
    BORDER_SUBTLE: str = "rgba(255, 255, 255, 0.08)"
    SHADOW_ICE:    str = "0 0 20px rgba(125, 211, 252, 0.15)"


# ============================================================================
# TIPOGRAFÍA
# ============================================================================
@dataclass(frozen=True)
class Typography:
    DISPLAY: str = "'Syne', sans-serif"
    BODY:    str = "'DM Sans', sans-serif"
    DATA:    str = "'JetBrains Mono', monospace"
    ACCENT:  str = "'Space Grotesk', sans-serif"


# ============================================================================
# CONFIGURACIÓN DE APP
# ============================================================================
def _find_recipes_file() -> str:
    """Busca el JSON de recetas en data/ primero, luego en la raíz."""
    candidates = [
        "data/recetas_backend_proceso_ultra.json",
        "recetas_backend_proceso_ultra.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Devuelve la ruta preferida aunque no exista (fallará con mensaje claro)
    return candidates[0]


@dataclass
class AppConfig:
    """Configuración funcional de la aplicación."""

    # ── Google Cloud ────────────────────────────────────────────────────────
    # Busca en variable de entorno primero; si no, usa el valor por defecto.
    # Antes de cada lab nuevo: export GOOGLE_CLOUD_PROJECT=<nuevo-project-id>
    VERTEX_PROJECT_ID: str = field(
        default_factory=lambda: os.environ.get(
            "GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-f46aab7b85f0"
        )
    )
    VERTEX_LOCATION: str = "us-central1"

    # ── Paths ────────────────────────────────────────────────────────────────
    DATA_DIR:      str = "data"
    RECIPES_FILE:  str = "data/recetas_backend_proceso_ultra.json"
    RATINGS_FILE:  str = "data/ratings.csv"
    SESSION_FILE:  str = "data/session_state.json"
    LOG_FILE:      str = "data/app.log"

    # ── Gemini / Vision ──────────────────────────────────────────────────────
    GEMINI_MODEL:       str   = "gemini-2.0-flash-001"
    DEFAULT_CONFIDENCE: float = 0.5
    MAX_INGREDIENTS:    int   = 20

    # ── Recomendaciones ──────────────────────────────────────────────────────
    DEFAULT_N_RECIPES: int = 5
    MAX_N_RECIPES:     int = 10

    # ── Modos de operación ───────────────────────────────────────────────────
    # IMPORTANTE: usamos strings literales de color, NO Colors.X,
    # porque el dataclass Colors no está instanciado en este punto.
    MODES: Dict[str, Dict] = field(default_factory=lambda: {
        "survival": {
            "name": "Survival",
            "icon": "🧊",
            "description": "Cocina con lo que tienes AHORA",
            "color": "#7dd3fc",       # ICE_BLUE
            "accent": "#14b8a6",      # TEAL_AURORA
            "max_missing": 2,
            "show_techniques": False,
            "show_pairings": False,
            "show_plating": False,
        },
        "chef": {
            "name": "Chef Pro",
            "icon": "👨‍🍳",
            "description": "Experiencias gastronómicas completas",
            "color": "#a78bfa",       # PURPLE_NEBULA
            "accent": "#c4b5fd",      # Purple más claro para hover
            "max_missing": 5,
            "show_techniques": True,
            "show_pairings": True,
            "show_plating": True,
        },
    })

    def ensure_dirs(self):
        """Crea directorios necesarios si no existen."""
        os.makedirs(self.DATA_DIR, exist_ok=True)

    def get_mode(self, mode_key: str) -> Dict:
        """Devuelve la config de un modo con fallback a survival."""
        return self.MODES.get(mode_key, self.MODES["survival"])


# ============================================================================
# INSTANCIAS GLOBALES — importar desde cualquier módulo
# ============================================================================
COLORS = Colors()
TYPO   = Typography()
CONFIG = AppConfig()
CONFIG.ensure_dirs()
#!/usr/bin/env python3
"""
EatguAI
Entry point unificado para Vertex AI Workbench.
"""

import os
import sys
import logging
import tempfile

os.makedirs("data", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("FridgeGuide")

import gradio as gr

from config import CONFIG, COLORS
from models import Rating
from core.vision import detectar_ingredientes, VisionError
from core.recommender import RecipeRecommender
from components.ui_renderer import UIRenderer
from components.analytics import SimpleStore

# ── Inicializar componentes globales ─────────────────────────────────────────
logger.info("🧊 Iniciando EatguAI...")

store      = SimpleStore()
renderer   = UIRenderer()
recommender = RecipeRecommender()

CURRENT_MODE = "survival"

# ── Opciones de filtros ──────────────────────────────────────────────────────
OPCIONES_TIEMPO   = ["Todos", "15 min", "30 min", "45 min", "60 min"]
OPCIONES_FALTAN   = ["Todos", "0", "1", "2", "3"]
TIEMPO_MAP        = {"Todos": None, "15 min": 15, "30 min": 30, "45 min": 45, "60 min": 60}
FALTAN_MAP        = {"Todos": None, "0": 0, "1": 1, "2": 2, "3": 3}


# =============================================================================
# FUNCIONES DE NEGOCIO
# =============================================================================

def analizar_nevera(imagen, n_recetas, confianza, filtro_tiempo, filtro_faltan, modo):
    """Pipeline completo: imagen → ingredientes → recetas."""
    global CURRENT_MODE
    CURRENT_MODE = modo

    if imagen is None:
        yield (
            renderer.render_empty_state("Sube una foto para comenzar", "default"),
            renderer.render_empty_state("Las recetas aparecerán aquí", "default"),
            {},
            gr.update(choices=[]),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            gr.update(interactive=True),
        )
        return

    # Efecto de escaneo mientras procesa
    yield (
        renderer.render_scanning(),
        renderer.render_empty_state("Procesando imagen...", "default"),
        {},
        gr.update(choices=[]),
        gr.update(visible=False),
        gr.update(value="", visible=False),
        gr.update(interactive=True),
    )

    try:
        # 1. Guardar imagen temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            imagen.save(tmp.name)
            tmp_path = tmp.name

        # 2. Detectar ingredientes
        conf_map  = {"Bajo": 0.3, "Medio": 0.5, "Alto": 0.75}
        min_conf  = conf_map.get(confianza, 0.5)
        ingredientes = detectar_ingredientes(tmp_path)
        os.unlink(tmp_path)

        # Filtrar por confianza
        ingredientes = [i for i in ingredientes if i.confidence >= min_conf]

        if not ingredientes:
            yield (
                renderer.render_empty_state("No se detectaron ingredientes", "error"),
                renderer.render_empty_state("Prueba con mejor iluminación", "no_results"),
                {},
                gr.update(choices=[]),
                gr.update(visible=False),
                gr.update(value="", visible=False),
                gr.update(interactive=True),
            )
            return

        # 3. Registrar búsqueda en analytics
        nombres = [i.name for i in ingredientes]
        store.record_search(nombres)

        # 4. Renderizar ingredientes
        ing_html = renderer.render_ingredients_grid(ingredientes)

        # 5. Construir filtros
        filtros = {
            "max_tiempo":    TIEMPO_MAP.get(filtro_tiempo),
            "max_faltantes": FALTAN_MAP.get(filtro_faltan),
        }

        # 6. Recomendar
        resultados = recommender.recommend(
            nombres,
            n=int(n_recetas),
            modo=modo,
            filtros=filtros,
        )

        if not resultados:
            yield (
                ing_html,
                renderer.render_empty_state("No hay recetas con esos filtros", "no_results"),
                {},
                gr.update(choices=[]),
                gr.update(visible=False),
                gr.update(value="", visible=False),
                gr.update(interactive=True),
            )
            return

        # 7. Renderizar recetas
        recetas_html = renderer.render_recipes_list(resultados, modo=modo)

        # 8. Estado para valoraciones
        nombres_recetas = [r.receta.nombre for r in resultados]
        estado = {
            r.receta.nombre: {
                "match":        f"{r.porcentaje_match*100:.0f}%",
                "ingredientes": ", ".join(nombres),
            }
            for r in resultados
        }

        yield (
            ing_html,
            recetas_html,
            estado,
            gr.update(choices=nombres_recetas, value=None),
            gr.update(visible=True),
            gr.update(value="", visible=False),
            gr.update(interactive=True),
        )

    except VisionError as e:
        yield (
            renderer.render_empty_state(f"Error de visión: {e}", "error"),
            renderer.render_empty_state("Inténtalo de nuevo", "error"),
            {},
            gr.update(choices=[]),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            gr.update(interactive=True),
        )
    except Exception as e:
        yield (
            renderer.render_empty_state("Error inesperado", "error"),
            renderer.render_empty_state(str(e), "error"),
            {},
            gr.update(choices=[]),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            gr.update(interactive=True),
        )


def recomendar_manual(ingredientes_str, n_recetas, filtro_tiempo, filtro_faltan, modo):
    """Recomendación sin foto, solo texto."""
    if not ingredientes_str.strip():
        return renderer.render_empty_state("Escribe al menos un ingrediente.")

    nombres = [i.strip().lower() for i in ingredientes_str.split(",") if i.strip()]

    filtros = {
        "max_tiempo":    TIEMPO_MAP.get(filtro_tiempo),
        "max_faltantes": FALTAN_MAP.get(filtro_faltan),
    }

    resultados = recommender.recommend(nombres, n=int(n_recetas), modo=modo, filtros=filtros)

    if not resultados:
        return renderer.render_empty_state("No hay recetas con esos ingredientes.")

    return renderer.render_recipes_list(resultados, modo=modo)


def guardar_rating(receta_sel, gusto, relevancia, estado):
    """Guarda valoración en CSV."""
    if not receta_sel or not gusto or not relevancia:
        return (
            gr.update(value="<span style='color:var(--warning);'>⚠️ Completa todos los campos.</span>", visible=True),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
        )

    info   = estado.get(receta_sel, {})
    rating = Rating(
        receta=receta_sel,
        match_pct=info.get("match", ""),
        ingredientes_detectados=info.get("ingredientes", ""),
        gusto=gusto,
        relevancia=relevancia,
        modo=CURRENT_MODE,
        session_id=store.session.session_id,
    )
    store.add_rating(rating)
    return (
        gr.update(value=f"<span style='color:var(--success);'>✅ Guardado: {receta_sel}</span>", visible=True),
        gr.update(value=None),           # resetea dropdown
        gr.update(value=None),           # resetea gusto
        gr.update(value=None),           # resetea relevancia
        gr.update(interactive=False),    # deshabilita botón para no repetir
    )

def mostrar_analytics():
    """Renderiza dashboard de sesión."""
    data = store.get_summary()
    top_ing_html = "".join(
        f"<span style='background:rgba(125,211,252,0.1); color:var(--ice-blue); "
        f"padding:4px 12px; border-radius:12px; font-size:0.85em;'>"
        f"{ing} ({count})</span>"
        for ing, count in data["top_ingredientes"]
    )
    return f"""
    <div class="fade-in">
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px;">
            <div class="glass-panel" style="padding:20px; text-align:center;">
                <div style="font-size:2em;">🔍</div>
                <div style="font-family:var(--font-data); font-size:1.5em; color:var(--ice-blue);">{data['busquedas']}</div>
                <div class="text-label">Búsquedas</div>
            </div>
            <div class="glass-panel" style="padding:20px; text-align:center;">
                <div style="font-size:2em;">⭐</div>
                <div style="font-family:var(--font-data); font-size:1.5em; color:var(--ice-blue);">{data['ratings']}</div>
                <div class="text-label">Valoraciones</div>
            </div>
            <div class="glass-panel" style="padding:20px; text-align:center;">
                <div style="font-size:2em;">⏱️</div>
                <div style="font-family:var(--font-data); font-size:1.5em; color:var(--ice-blue);">{data['tiempo_activo']}</div>
                <div class="text-label">Minutos activo</div>
            </div>
            <div class="glass-panel" style="padding:20px; text-align:center;">
                <div style="font-size:2em;">🆔</div>
                <div style="font-family:var(--font-data); font-size:0.9em; color:var(--ice-blue);">{data['session_id'][:8]}...</div>
                <div class="text-label">Sesión</div>
            </div>
        </div>
        <div class="glass-panel" style="padding:20px;">
            <div class="text-label" style="margin-bottom:12px;">Ingredientes más buscados</div>
            <div style="display:flex; flex-wrap:wrap; gap:8px;">{top_ing_html}</div>
        </div>
    </div>
    """


# =============================================================================
# CSS
# =============================================================================
CSS_CUSTOM = f"""

/* ═══════════════════════════════════════════════════════════════════════════ */
/* BASE — Fondo oscuro global y variables CSS                                 */
/* ═══════════════════════════════════════════════════════════════════════════ */

body,
.gradio-container,
.gradio-container-6-8-0,
.svelte-99kmwu,
.gradio-container.svelte-99kmwu,
.main,
#root {{
    background: {COLORS.BG_PRIMARY} !important;
    background-color: {COLORS.BG_PRIMARY} !important;
}}

* {{
    --bg-primary: {COLORS.BG_PRIMARY};
    --bg-secondary: {COLORS.BG_SECONDARY};
    --ice-blue: {COLORS.ICE_BLUE};
    --purple-nebula: {COLORS.PURPLE_NEBULA};
    --success: {COLORS.SUCCESS};
    --warning: {COLORS.WARNING};
    --error: {COLORS.ERROR};
    --text-primary: {COLORS.TEXT_PRIMARY};
    --text-secondary: {COLORS.TEXT_SECONDARY};
    --text-muted: {COLORS.TEXT_MUTED};
    --border-subtle: {COLORS.BORDER_SUBTLE};
    --border-glow: {COLORS.BORDER_GLOW};
    --font-body: 'DM Sans', sans-serif;
    --font-display: 'Syne', sans-serif;
    --font-data: 'JetBrains Mono', monospace;
    --font-accent: 'Space Grotesk', sans-serif;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* CONTENEDOR PRINCIPAL                                                        */
/* ═══════════════════════════════════════════════════════════════════════════ */

.gradio-container-6-8-0 {{
    border: 1px solid rgba(125, 211, 252, 0.2) !important;
    border-radius: 20px !important;
    box-shadow:
        0 0 40px rgba(125, 211, 252, 0.1),
        0 0 80px rgba(125, 211, 252, 0.05),
        inset 0 0 40px rgba(125, 211, 252, 0.02) !important;
    overflow: hidden !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* BLOCKS — Contenedores con brillo                                            */
/* ═══════════════════════════════════════════════════════════════════════════ */

.block,
.block.svelte-1plpy97 {{
    background: {COLORS.BG_SECONDARY} !important;
    border: 1px solid rgba(125, 211, 252, 0.25) !important;
    border-radius: 16px !important;
    border-style: none !important;
    padding: 16px !important;
    margin: 0 !important;
    box-shadow:
        0 0 18px rgba(125, 211, 252, 0.15),
        0 0 40px rgba(125, 211, 252, 0.06),
        inset 0 0 20px rgba(125, 211, 252, 0.03) !important;
    transition: all 0.3s ease !important;
}}

.block:hover {{
    border-color: rgba(125, 211, 252, 0.45) !important;
    box-shadow:
        0 0 28px rgba(125, 211, 252, 0.25),
        0 0 60px rgba(125, 211, 252, 0.1),
        inset 0 0 20px rgba(125, 211, 252, 0.05) !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* LAYOUT — Rows, columns, forms, grupos                                       */
/* ═══════════════════════════════════════════════════════════════════════════ */

.gradio-row {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    gap: 12px !important;
    margin: 0 !important;
    padding: 0 !important;
}}

.gradio-row > .column,
.gradio-group,
fieldset,
.group,
.form,
.form.svelte-d5xbca {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}}

.form {{ gap: 8px !important; }}
.wrap {{ padding: 16px !important; }}

/* Fieldset radio — flex para centrar */
fieldset.block.svelte-1plpy97,
fieldset[style*="border-style: solid"] {{
    border-style: none !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* LABELS Y TEXTOS                                                             */
/* ═══════════════════════════════════════════════════════════════════════════ */

[data-testid="block-info"],
label .label-text,
label span,
.form .label span,
.gradio-dropdown label,
.gradio-slider label,
.gradio-radio label,
.gradio-image label,
.wrap .label span {{
    color: {COLORS.ICE_BLUE} !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.75em !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    opacity: 0.9 !important;
    margin-bottom: 8px !important;
}}

.text-label {{
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.75em !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    color: {COLORS.ICE_BLUE} !important;
    opacity: 0.9 !important;
}}

/* Label flotante imagen */
label.svelte-19djge9 {{
    color: {COLORS.ICE_BLUE} !important;
    background: {COLORS.BG_SECONDARY} !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.75em !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* RADIO BUTTONS                                                               */
/* ═══════════════════════════════════════════════════════════════════════════ */

.gradio-radio .wrap,
.gradio-radio .container {{
    background: transparent !important;
    border: none !important;
    padding: 8px 0 !important;
}}

.wrap.svelte-e4x47i {{
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 8px !important;
    padding: 8px 4px !important;
    align-items: center !important;
}}

input[type="radio"].svelte-19qdtil {{ display: none !important; }}

label.svelte-19qdtil {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 8px 12px !important;
    border-radius: 8px !important;
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(125,211,252,0.15) !important;
    cursor: pointer !important;
    flex: 1 !important;
    font-size: 0.85em !important;
    text-align: center !important;
}}

label.svelte-19qdtil.selected {{
    background: rgba(125,211,252,0.12) !important;
    border-color: rgba(125,211,252,0.4) !important;
    color: {COLORS.ICE_BLUE} !important;
}}

label.svelte-19qdtil span.svelte-19qdtil {{
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
    display: block !important;
    text-align: center !important;
    width: 100% !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* SLIDER                                                                      */
/* ═══════════════════════════════════════════════════════════════════════════ */

.gradio-slider .wrap {{
    background: transparent !important;
    border: none !important;
    padding: 8px 0 !important;
}}

input[type="range"] {{
    accent-color: {COLORS.ICE_BLUE} !important;
    height: 6px !important;
    background: rgba(255,255,255,0.1) !important;
    border-radius: 3px !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* DROPDOWN                                                                    */
/* ═══════════════════════════════════════════════════════════════════════════ */

.svelte-1xfsv4t.container {{ min-height: unset !important; }}

.wrap.svelte-1xfsv4t {{
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    min-height: unset !important;
}}

.wrap-inner.svelte-1xfsv4t {{
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(125,211,252,0.15) !important;
    border-radius: 8px !important;
    padding: 6px 8px !important;
    transition: all 0.2s ease !important;
}}

.wrap-inner.svelte-1xfsv4t:hover {{
    background: rgba(125,211,252,0.08) !important;
    border-color: rgba(125,211,252,0.3) !important;
}}

.wrap-inner.svelte-1xfsv4t input {{
    background: transparent !important;
    border: none !important;
    color: {COLORS.TEXT_PRIMARY} !important;
    font-family: 'DM Sans', sans-serif !important;
}}

.dropdown-arrow {{ fill: {COLORS.ICE_BLUE} !important; opacity: 0.6 !important; }}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* INPUTS DE TEXTO                                                             */
/* ═══════════════════════════════════════════════════════════════════════════ */

textarea,
input[type="text"],
input[type="number"] {{
    background: {COLORS.BG_PRIMARY} !important;
    border: 1px solid rgba(125, 211, 252, 0.2) !important;
    color: {COLORS.TEXT_PRIMARY} !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
}}

textarea:focus, input:focus {{
    border-color: {COLORS.ICE_BLUE} !important;
    box-shadow: 0 0 0 3px rgba(125, 211, 252, 0.1) !important;
    outline: none !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* IMAGEN                                                                      */
/* ═══════════════════════════════════════════════════════════════════════════ */

.image-container.svelte-6uxbr3,
.upload-container.svelte-6uxbr3 {{
    background: {COLORS.BG_SECONDARY} !important;
}}

.source-selection.svelte-exvkcd {{ background: {COLORS.BG_SECONDARY} !important; }}
.icon.svelte-exvkcd {{ color: {COLORS.ICE_BLUE} !important; opacity: 0.6 !important; }}
.icon-button-wrapper.svelte-1pnho82 {{ background: transparent !important; }}
.icon-button.svelte-3jwzs9 {{
    background: {COLORS.BG_SECONDARY} !important;
    color: {COLORS.ICE_BLUE} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* BOTONES                                                                     */
/* ═══════════════════════════════════════════════════════════════════════════ */

button.lg.primary,
button.svelte-xzq5jh.primary {{
    background: linear-gradient(135deg, {COLORS.ICE_BLUE}, {COLORS.PURPLE_NEBULA}) !important;
    color: {COLORS.BG_PRIMARY} !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    box-shadow: 0 4px 20px rgba(125, 211, 252, 0.3) !important;
}}

button.lg.primary:hover,
button.svelte-xzq5jh.primary:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(125, 211, 252, 0.4) !important;
    filter: brightness(1.1) !important;
}}

/* Botón secundario base */
button.secondary {{
    background: rgba(125, 211, 252, 0.1) !important;
    border: 1px solid rgba(125, 211, 252, 0.3) !important;
    color: {COLORS.ICE_BLUE} !important;
    border-radius: 10px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    font-size: 0.85em !important;
}}

button.secondary:hover {{
    background: rgba(125, 211, 252, 0.2) !important;
    border-color: rgba(125, 211, 252, 0.5) !important;
}}

/* Botón guardar — amarillo (más específico, sobreescribe el secundario) */
button.secondary.svelte-xzq5jh {{
    background: linear-gradient(135deg, {COLORS.WARNING}, #f59e0b) !important;
    color: {COLORS.BG_PRIMARY} !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 20px rgba(251, 191, 36, 0.3) !important;
}}

button.secondary.svelte-xzq5jh:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(251, 191, 36, 0.4) !important;
    filter: brightness(1.1) !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* HTML INYECTADO                                                              */
/* ═══════════════════════════════════════════════════════════════════════════ */

.gradio-html {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* ANIMACIONES                                                                 */
/* ═══════════════════════════════════════════════════════════════════════════ */

@keyframes float {{
    0%, 100% {{ transform: translateY(0px); }}
    50% {{ transform: translateY(-10px); }}
}}
@keyframes dotPulse {{
    0%, 80%, 100% {{ transform: scale(0.6); opacity: 0.4; }}
    40% {{ transform: scale(1); opacity: 1; box-shadow: 0 0 10px var(--ice-blue); }}
}}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* TABS — estandarizar colores y eliminar barra blanca                         */
/* ═══════════════════════════════════════════════════════════════════════════ */

/* Contenedor de tabs — fondo oscuro, sin borde blanco inferior */
.tab-wrapper.svelte-11gaq1,
div.tab-wrapper {{
    background: {COLORS.BG_PRIMARY} !important;
    border-bottom: 1px solid rgba(125, 211, 252, 0.15) !important;
    padding: 0 8px !important;
}}

/* Contenedor interno */
.tab-container.svelte-11gaq1 {{
    background: transparent !important;
    border: none !important;
    gap: 4px !important;
}}

/* Todos los botones de tab — estado inactivo */
.tab-wrapper button.svelte-11gaq1,
div[role="tablist"] button {{
    background: transparent !important;
    color: rgba(125, 211, 252, 0.45) !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 10px 20px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.9em !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}}

/* Hover sobre tab inactivo */
.tab-wrapper button.svelte-11gaq1:hover,
div[role="tablist"] button:hover {{
    color: rgba(125, 211, 252, 0.8) !important;
    background: rgba(125, 211, 252, 0.05) !important;
    border-bottom: 2px solid rgba(125, 211, 252, 0.3) !important;
}}

/* Tab activo — igual que "Analizar Foto" */
.tab-wrapper button.svelte-11gaq1.selected,
div[role="tablist"] button[aria-selected="true"] {{
    background: rgba(125, 211, 252, 0.1) !important;
    color: {COLORS.ICE_BLUE} !important;
    border-bottom: 2px solid {COLORS.ICE_BLUE} !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 12px rgba(125, 211, 252, 0.15) !important;
}}

/* Eliminar la barra/línea blanca debajo del tab-nav */
.tabs.svelte-11gaq1 > div:first-child,
.tabitem.svelte-11gaq1 {{
    border-top: none !important;
    box-shadow: none !important;
}}

/* Fondo del panel de contenido de cada tab */
.tabitem.svelte-11gaq1,
div.tabitem {{
    background: {COLORS.BG_PRIMARY} !important;
    border: none !important;
    padding-top: 16px !important;
}}

div.tab-container.svelte-11gaq1::after {{
    display: none !important;
}}

"""

# =============================================================================
# INTERFAZ GRADIO
# =============================================================================

import base64
with open("logo_blanco.png", "rb") as f:
    LOGO_B64 = base64.b64encode(f.read()).decode()

import components.ui_renderer as _ui_mod
_ui_mod.LOGO_B64 = LOGO_B64

with gr.Blocks(title="🧊 EatguAI 🧊", theme=gr.themes.Base(), css=CSS_CUSTOM) as demo:

    header      = gr.HTML(renderer.render_header("survival"))
    estado_vals = gr.State({})

    with gr.Tabs():

        # ── TAB 1: FOTO ──────────────────────────────────────────────────────
        with gr.Tab("Analizar Foto"):
            with gr.Row():

                # COLUMNA 1 — Modo e imagen
                with gr.Column(scale=1, min_width=200):
                    modo_radio   = gr.Radio(
                        choices=["survival", "chef"],
                        value="survival",
                        label="Modo",
                    )
                    imagen_input = gr.Image(type="pil", label="Foto de tu nevera", height=300)
                    analizar_btn = gr.Button("Analizar nevera", variant="primary", size="lg")

                # COLUMNA 2 — Filtros y valoración
                with gr.Column(scale=1, min_width=200):
                    n_slider      = gr.Slider(1, 10, value=5, step=1, label="Nº recetas")
                    conf_radio = gr.Radio(
                        ["Bajo", "Medio", "Alto"],
                        value="Medio",
                        label="Precisión",
                        type="value",
                        interactive=True,
                        container=True,
                    )
                    filtro_tiempo = gr.Dropdown(choices=OPCIONES_TIEMPO, value="Todos", label="⏱ Tiempo máx.")
                    filtro_faltan = gr.Dropdown(choices=OPCIONES_FALTAN, value="Todos", label="❌ Máx. faltantes")

                    with gr.Column(visible=False) as val_group:
                        receta_dd   = gr.Dropdown(choices=[], label="⭐ Valorar receta")
                        gusto_radio = gr.Radio(["👍 Me gusta", "👎 No me gusta"], label="¿Te gustó?")
                        rel_radio   = gr.Radio(["Usa lo que tengo", "Me faltan cosas"], label="¿Es relevante?")
                        guardar_btn = gr.Button("Guardar valoración", variant="secondary")
                    msg_val = gr.HTML(value="", visible=False)

                # COLUMNA 3 — Resultados
                with gr.Column(scale=2, min_width=400):
                    out_ing = gr.HTML()
                    out_rec = gr.HTML(value=renderer.render_empty_state())

            # Eventos TAB 1
            analizar_btn.click(
                fn=analizar_nevera,
                inputs=[imagen_input, n_slider, conf_radio, filtro_tiempo, filtro_faltan, modo_radio],
                outputs=[out_ing, out_rec, estado_vals, receta_dd, val_group, msg_val, guardar_btn],
            )
            guardar_btn.click(
                fn=guardar_rating,
                inputs=[receta_dd, gusto_radio, rel_radio, estado_vals],
                outputs=[msg_val, receta_dd, gusto_radio, rel_radio, guardar_btn],
            )
            modo_radio.change(
                fn=lambda m: renderer.render_header(m),
                inputs=modo_radio,
                outputs=header,
            )

        # ── TAB 2: MANUAL ────────────────────────────────────────────────────
        with gr.Tab("Manual"):
            with gr.Row():
                manual_ing = gr.Textbox(
                    label="Ingredientes (separados por coma)",
                    placeholder="huevo, tomate, queso...",
                    lines=2, scale=3,
                )
                n_manual = gr.Slider(1, 10, value=5, step=1, label="Nº recetas", scale=1)
            with gr.Row():
                filtro_tiempo_m = gr.Dropdown(choices=OPCIONES_TIEMPO, value="Todos", label="⏱ Tiempo máx.")
                filtro_faltan_m = gr.Dropdown(choices=OPCIONES_FALTAN, value="Todos", label="❌ Máx. faltantes")
            modo_manual = gr.Radio(choices=["survival", "chef"], value="survival", label="Modo")
            manual_btn  = gr.Button("🍳 Buscar recetas", variant="primary")
            manual_out  = gr.HTML()

            manual_btn.click(
                fn=recomendar_manual,
                inputs=[manual_ing, n_manual, filtro_tiempo_m, filtro_faltan_m, modo_manual],
                outputs=manual_out,
            )

        # ── TAB 3: ANALYTICS ─────────────────────────────────────────────────
        with gr.Tab("Estadísticas"):
            refresh_btn = gr.Button("Actualizar dashboard")
            dashboard   = gr.HTML()
            export_btn  = gr.Button("Exportar datos")
            export_txt  = gr.Textbox(
                label="Copia esto antes de destruir el VM",
                lines=10,
            )
            refresh_btn.click(fn=mostrar_analytics, outputs=dashboard)
            export_btn.click(fn=lambda: store.export_message(), outputs=export_txt)

    gr.HTML(f"""
    <div style="text-align:center; padding:16px 20px 12px; 
                border-top:1px solid var(--border-subtle); margin-top:20px;">
        <div style="font-family:var(--font-body); font-size:0.8em; 
                    color:var(--text-muted); margin-bottom:4px; letter-spacing:1px;">
            Creado por
        </div>
        <div style="font-family:var(--font-accent); font-size:0.95em; 
                    color:var(--ice-blue); margin-bottom:8px; letter-spacing:0.5px;">
            Alonso Arredondo · Begoña Chamorro · Carolina Gamboa · Cesar Morales · Julián Álvarez
        </div>
        <div style="font-family:var(--font-data); font-size:1em; color:var(--text-muted);">
            EatguAI · Sesión: {store.session.session_id}
        </div>
    </div>
    """)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
        allowed_paths=["."],
    )

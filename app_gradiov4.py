#!/usr/bin/env python3
"""
Fridge Survival Guide - Pro Edition
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
logger.info("🧊 Iniciando Fridge Survival Guide Pro...")

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
            renderer.render_empty_state("Sube una foto de tu nevera"),
            renderer.render_empty_state(),
            {},
            gr.update(choices=[]),
            gr.update(visible=False),
        )
        return

    # Efecto de escaneo mientras procesa
    yield (
        renderer.render_scanning(),
        "<p style='color:var(--ice-blue); text-align:center; padding:20px;'>Procesando imagen...</p>",
        {},
        gr.update(choices=[]),
        gr.update(visible=False),
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
                "",
                renderer.render_empty_state("No se detectaron ingredientes. Prueba con mejor iluminación."),
                {},
                gr.update(choices=[]),
                gr.update(visible=False),
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
                renderer.render_empty_state("No hay recetas con esos ingredientes y filtros."),
                {},
                gr.update(choices=[]),
                gr.update(visible=False),
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
        )

    except VisionError as e:
        logger.error(f"Error de visión: {e}")
        yield (
            "",
            f"<p style='color:var(--error); padding:20px;'>❌ Error analizando imagen: {e}</p>",
            {},
            gr.update(choices=[]),
            gr.update(visible=False),
        )
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        yield (
            "",
            f"<p style='color:var(--error); padding:20px;'>❌ Error inesperado: {e}</p>",
            {},
            gr.update(choices=[]),
            gr.update(visible=False),
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
        return "<span style='color:var(--warning);'>⚠️ Completa todos los campos.</span>"

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
    return f"<span style='color:var(--success);'>✅ Guardado: {receta_sel}</span>"


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
{renderer.get_base_styles()}

/* ─────────────────────────────────────────────────────────────────────────── */
/* CONTENEDOR PRINCIPAL */
/* ─────────────────────────────────────────────────────────────────────────── */

.gradio-container {{
    background: {COLORS.BG_PRIMARY} !important;
    font-family: 'DM Sans', sans-serif !important;
}}

/* ─────────────────────────────────────────────────────────────────────────── */
/* TABS - Mismo estilo que "cocina con lo que tienes ahora" */
/* ─────────────────────────────────────────────────────────────────────────── */

.tab-nav {{
    background: rgba(255,255,255,0.03) !important;
    border-radius: 16px !important;
    padding: 6px !important;
    margin-bottom: 24px !important;
    border: 1px solid rgba(125, 211, 252, 0.15) !important;
}}

.tab-nav button {{
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.75em !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    color: rgba(125, 211, 252, 0.6) !important;
    border-radius: 12px !important;
    padding: 12px 24px !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.3s ease !important;
}}

.tab-nav button:hover {{
    color: rgba(125, 211, 252, 0.85) !important;
    background: rgba(125, 211, 252, 0.05) !important;
}}

.tab-nav button.selected {{
    color: {COLORS.ICE_BLUE} !important;
    background: rgba(125, 211, 252, 0.12) !important;
    box-shadow: 0 0 20px rgba(125, 211, 252, 0.15) !important;
    font-weight: 600 !important;
}}

/* ─────────────────────────────────────────────────────────────────────────── */
/* LABELS DE FILTROS - Mismo estilo que subtítulo del header */
/* ─────────────────────────────────────────────────────────────────────────── */

/* Todos los labels de Gradio */
label .label-text,
label span,
.form .label span,
.gradio-dropdown label,
.gradio-slider label,
.gradio-radio label,
.gradio-checkbox label,
.gradio-textbox label,
.gradio-number label,
.gradio-image label,
input[type="number"] + label,
.wrap .label span {{
    color: {COLORS.ICE_BLUE} !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.75em !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    opacity: 0.9 !important;
    margin-bottom: 8px !important;
    display: block !important;
}}

/* Labels específicos de dropdown y radio */
.gradio-dropdown .label span,
.gradio-radio .label span,
.gradio-slider .label span {{
    color: {COLORS.ICE_BLUE} !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.75em !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
}}

/* ─────────────────────────────────────────────────────────────────────────── */
/* CONTENEDORES (BLOCKS) - Sin espacios entre ellos, solo bordes brillantes */
/* ─────────────────────────────────────────────────────────────────────────── */

/* Cada componente individual envuelto en .block */
.block {{
    background: {COLORS.BG_SECONDARY} !important;
    border: 1px solid rgba(125, 211, 252, 0.25) !important;
    border-radius: 16px !important;
    box-shadow: 
        0 0 18px rgba(125, 211, 252, 0.15),
        0 0 40px rgba(125, 211, 252, 0.06),
        inset 0 0 20px rgba(125, 211, 252, 0.03) !important;
    margin: 0 !important;  /* Sin margen entre contenedores */
    transition: all 0.3s ease !important;
}}

.block:hover {{
    border-color: rgba(125, 211, 252, 0.45) !important;
    box-shadow: 
        0 0 28px rgba(125, 211, 252, 0.25),
        0 0 60px rgba(125, 211, 252, 0.1),
        inset 0 0 20px rgba(125, 211, 252, 0.05) !important;
}}

/* Quitar padding interno excesivo de los wrap */
.wrap {{
    padding: 12px !important;
}}

/* ─────────────────────────────────────────────────────────────────────────── */
/* ROWS - Sin fondo, sin bordes, solo gap controlado */
/* ─────────────────────────────────────────────────────────────────────────── */

.gradio-row {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    gap: 12px !important;  /* Separación entre columnas, no espacio vacío */
    margin: 0 !important;
    padding: 0 !important;
}}

/* Las columnas dentro del row */
.gradio-row > .column {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}}

/* ─────────────────────────────────────────────────────────────────────────── */
/* GRUPOS Y FIELDSETS - Sin fondo gris */
/* ─────────────────────────────────────────────────────────────────────────── */

.gradio-group,
fieldset,
.group {{
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
}}

/* ─────────────────────────────────────────────────────────────────────────── */
/* COMPONENTES INTERNOS - Sin bordes propios, heredan del .block */
/* ─────────────────────────────────────────────────────────────────────────── */

/* Radio buttons */
.gradio-radio .wrap,
.gradio-radio .container {{
    background: transparent !important;
    border: none !important;
    padding: 8px 0 !important;
}}

/* Radio items individuales */
.radio-item {{
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(125, 211, 252, 0.15) !important;
    border-radius: 8px !important;
    margin: 4px 0 !important;
    padding: 8px 12px !important;
    transition: all 0.2s ease !important;
}}

.radio-item:hover {{
    background: rgba(125, 211, 252, 0.08) !important;
    border-color: rgba(125, 211, 252, 0.3) !important;
}}

.radio-item.selected {{
    background: rgba(125, 211, 252, 0.15) !important;
    border-color: rgba(125, 211, 252, 0.4) !important;
    color: {COLORS.ICE_BLUE} !important;
}}

/* Slider */
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

/* Dropdown */
.gradio-dropdown .wrap {{
    background: {COLORS.BG_PRIMARY} !important;
    border: 1px solid rgba(125, 211, 252, 0.2) !important;
    border-radius: 10px !important;
}}

.gradio-dropdown .wrap:hover {{
    border-color: rgba(125, 211, 252, 0.4) !important;
}}

/* Input de texto */
textarea,
input[type="text"],
input[type="number"] {{
    background: {COLORS.BG_PRIMARY} !important;
    border: 1px solid rgba(125, 211, 252, 0.2) !important;
    color: {COLORS.TEXT_PRIMARY} !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
}}

textarea:focus,
input:focus {{
    border-color: {COLORS.ICE_BLUE} !important;
    box-shadow: 0 0 0 3px rgba(125, 211, 252, 0.1) !important;
    outline: none !important;
}}

/* Imagen */
.gradio-image .wrap {{
    background: {COLORS.BG_SECONDARY} !important;
    border: 1px solid rgba(125, 211, 252, 0.25) !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    box-shadow: 
        0 0 18px rgba(125, 211, 252, 0.15),
        inset 0 0 20px rgba(125, 211, 252, 0.03) !important;
}}

/* Botón primario */
button.primary {{
    background: linear-gradient(135deg, rgba(125,211,252,0.9), rgba(167,139,250,0.9)) !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    color: {COLORS.BG_PRIMARY} !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 20px rgba(125, 211, 252, 0.3) !important;
}}

button.primary:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(125, 211, 252, 0.4) !important;
    filter: brightness(1.1) !important;
}}

/* Botón secundario */
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

/* Quitar espacios de HTML injectado */
.gradio-html {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}}

/* Separador invisible (usa esto en lugar de gr.HTML con height) */
.spacer {{
    height: 8px !important;
    background: transparent !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
}}
"""

# =============================================================================
# INTERFAZ GRADIO
# =============================================================================

with gr.Blocks(title="🧊 Fridge Survival Guide Pro 🧊", theme=gr.themes.Base(), css=CSS_CUSTOM) as demo:

    header      = gr.HTML(renderer.render_header("survival"))
    estado_vals = gr.State({})

    with gr.Tabs():

        # ── TAB 1: FOTO ──────────────────────────────────────────────────────
        with gr.Tab("Analizar Foto"):
            with gr.Row():

                # COLUMNA 1 — Modo e imagen
                with gr.Column(scale=1, min_width=250):
                    modo_radio   = gr.Radio(
                        choices=["survival", "chef"],
                        value="survival",
                        label="Modo",
                    )
                    imagen_input = gr.Image(type="pil", label="Foto de tu nevera", height=300)
                    analizar_btn = gr.Button("🔍 Analizar nevera", variant="primary", size="lg")

                # COLUMNA 2 — Filtros y valoración
                with gr.Column(scale=1, min_width=200):
                    n_slider      = gr.Slider(1, 10, value=5, step=1, label="Nº recetas")
                    conf_radio    = gr.Radio(["Bajo", "Medio", "Alto"], value="Medio", label="Precisión")
                    filtro_tiempo = gr.Dropdown(choices=OPCIONES_TIEMPO, value="Todos", label="⏱ Tiempo máx.")
                    filtro_faltan = gr.Dropdown(choices=OPCIONES_FALTAN, value="Todos", label="❌ Máx. faltantes")

                    with gr.Group(visible=False) as val_group:
                        gr.HTML("<hr style='border-color:rgba(125,211,252,0.1); margin:16px 0;'>")
                        receta_dd   = gr.Dropdown(choices=[], label="⭐ Valorar receta")
                        gusto_radio = gr.Radio(["👍 Me gusta", "👎 No me gusta"], label="¿Te gustó?")
                        rel_radio   = gr.Radio(["Usa lo que tengo", "Me faltan cosas"], label="¿Es relevante?")
                        guardar_btn = gr.Button("Guardar valoración", variant="secondary")
                        msg_val     = gr.HTML()

                # COLUMNA 3 — Resultados
                with gr.Column(scale=2, min_width=400):
                    out_ing = gr.HTML()
                    out_rec = gr.HTML(value=renderer.render_empty_state())

            # Eventos TAB 1
            analizar_btn.click(
                fn=analizar_nevera,
                inputs=[imagen_input, n_slider, conf_radio, filtro_tiempo, filtro_faltan, modo_radio],
                outputs=[out_ing, out_rec, estado_vals, receta_dd, val_group],
            )
            guardar_btn.click(
                fn=guardar_rating,
                inputs=[receta_dd, gusto_radio, rel_radio, estado_vals],
                outputs=msg_val,
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
    <div style="text-align:center; padding:32px 20px; color:var(--text-muted);
                font-size:0.82em; border-top:1px solid var(--border-subtle); margin-top:40px;">
        🧊 Fridge Survival Guide Pro · Sesión: {store.session.session_id}
    </div>
    """)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
    )

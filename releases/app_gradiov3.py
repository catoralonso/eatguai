import gradio as gr
import tempfile
import os
import csv
from datetime import datetime

from vision import detect_gemini, clean_ingredients
from recommender import cargar_recetas, init_vectorizer, recomendar

# ──────────────────────────────────────────────
#  CARGA DE DATOS (una sola vez)
# ──────────────────────────────────────────────

recetas = cargar_recetas("recetas_backend_proceso_ultra.json")
vectorizer, tfidf_matrix = init_vectorizer(recetas)

RATINGS_CSV = "ratings.csv"

if not os.path.exists(RATINGS_CSV):
    with open(RATINGS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "receta", "match_pct", "ingredientes_detectados", "gusto", "relevancia"])

# ──────────────────────────────────────────────
#  CSS GLOBAL
# ──────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

body, .gradio-container {
    background-color: #0d0d14 !important;
    color: #e8e6f0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

h1, h2, h3 {
    font-family: 'Syne', sans-serif !important;
}

.gradio-container::before {
    content: '';
    position: fixed;
    inset: 0;
    background: radial-gradient(ellipse at 20% 20%, rgba(99,60,180,0.08) 0%, transparent 60%),
                radial-gradient(ellipse at 80% 80%, rgba(20,180,160,0.06) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
}

.block, .panel {
    background-color: #13131f !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 16px !important;
    box-shadow: 0 0 18px rgba(120,200,255,0.15),
                0 0 40px rgba(120,200,255,0.06),
                inset 0 0 20px rgba(120,200,255,0.03) !important;
    transition: border-color 0.3s, box-shadow 0.3s !important;
}

.block:hover, .panel:hover {
    border-color: rgba(255,255,255,0.45) !important;
    box-shadow: 0 0 28px rgba(120,200,255,0.25),
                0 0 60px rgba(120,200,255,0.1),
                inset 0 0 20px rgba(120,200,255,0.05) !important;
}

.tabs { background: transparent !important; }
.tab-nav { border-bottom: 1px solid #1e1e30 !important; }
.tab-nav button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    color: #666 !important;
    border-radius: 8px 8px 0 0 !important;
}
.tab-nav button.selected {
    color: #a78bfa !important;
    border-bottom: 2px solid #a78bfa !important;
    background: transparent !important;
}

button.primary {
    background: linear-gradient(135deg, #6d3cef, #a78bfa) !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
    transition: opacity 0.2s !important;
}
button.primary:hover { opacity: 0.88 !important; }

button.secondary {
    background: #1e1e30 !important;
    border: 1px solid #2e2e45 !important;
    color: #a78bfa !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
}

label { color: #a0a0b8 !important; font-size: 0.82em !important; font-weight: 500 !important; letter-spacing: 0.5px !important; }
input[type="text"], input[type="number"], input[type="email"], textarea, select { 
    background: #0d0d14 !important; 
    border-color: #1e1e30 !important; 
    color: #e8e6f0 !important; 
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0d0d14; }
::-webkit-scrollbar-thumb { background: #2e2e45; border-radius: 4px; }
"""

# ──────────────────────────────────────────────
#  HELPERS HTML
# ──────────────────────────────────────────────

def chips_ingredientes(cleaned):
    """Chips/tags visuales para ingredientes detectados."""
    if not cleaned:
        return ""

    def color_conf(conf):
        if conf >= 0.85:
            return ("#1a3a2a", "#4ade80", "🟢")
        elif conf >= 0.65:
            return ("#3a2e0a", "#fbbf24", "🟡")
        else:
            return ("#3a1a1a", "#f87171", "🔴")

    chips = ""
    for i in cleaned:
        bg, border, emoji = color_conf(i["confidence"])
        chips += f"""
        <span style="
            display:inline-flex; align-items:center; gap:5px;
            background:{bg}; border:1px solid {border}40;
            color:#e8e6f0; padding:5px 12px; border-radius:20px;
            font-size:0.85em; font-weight:500; margin:3px;
            font-family:'DM Sans',sans-serif;">
            {emoji} {i['name']} <span style="color:{border};font-size:0.75em;">({i['confidence']:.0%})</span>
        </span>"""

    return f"""
    <div style="padding:12px 0 8px;">
        <p style="font-family:'Syne',sans-serif; font-size:0.75em; font-weight:600;
                  letter-spacing:1px; color:#555; margin:0 0 10px 2px;">
            INGREDIENTES DETECTADOS
        </p>
        <div style="display:flex; flex-wrap:wrap; gap:2px;">
            {chips}
        </div>
    </div>
    """


def badge_match(match):
    """Barra de progreso visual para el % de match."""
    if match == 100:
        color = "#4ade80"
        label = "Tienes todo ✓"
    elif match >= 75:
        color = "#a3e635"
        label = f"{match:.0f}% disponible"
    elif match >= 50:
        color = "#fbbf24"
        label = f"{match:.0f}% disponible"
    else:
        color = "#f87171"
        label = f"{match:.0f}% disponible"

    return f"""
    <div style="margin:8px 0 4px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-size:0.72em; color:#777; font-family:'DM Sans',sans-serif;">{label}</span>
        </div>
        <div style="background:#1e1e30; border-radius:99px; height:5px; overflow:hidden;">
            <div style="background:{color}; width:{match}%; height:100%; border-radius:99px;"></div>
        </div>
    </div>
    """


def tarjeta_receta(r):
    """HTML de una tarjeta de receta expandible."""
    rec = r["receta"]
    match = r["porcentaje_match"] * 100
    badge_color = "#4ade80" if match == 100 else "#fbbf24" if match >= 50 else "#f87171"

    faltan = [i["item"] for i in rec["ingredientes_clave"]
              if i["item"].lower() not in [c.lower() for c in r["coincidencias"]]]
    n_faltan = len(faltan)
    faltan_txt = ", ".join(faltan) if faltan else "ninguno 🎉"

    import re
    def limpiar_paso(p):
        return re.sub(r'^[\d]+[\.\)]\s*', '', p)
    
    pasos = "".join([
        f"<li style='margin-bottom:10px; padding-left:4px; color:#c4c0d8; line-height:1.6;'>{limpiar_paso(p)}</li>"
        for p in rec.get("proceso_detallado", [])
    ])

    receta_id = rec['nombre'].replace(' ', '_').replace('/', '_').lower()
    nombre = rec["nombre"].title()
    dificultad = rec.get('dificultad', '').title()
    tiempo = rec.get('tiempo_min', '?')
    calorias = rec.get('calorias_aprox', '?')

    dif_color = {"Fácil": "#4ade80", "Media": "#fbbf24", "Difícil": "#f87171"}.get(dificultad, "#a78bfa")

    barra = badge_match(match)

    chips_faltan = "".join([
        f"<span style='background:#2a1a1a;border:1px solid #f8717140;color:#f87171;"
        f"padding:2px 8px;border-radius:12px;font-size:0.78em;margin:2px;display:inline-block;'>{x}</span>"
        for x in faltan
    ]) if faltan else "<span style='color:#4ade80;font-size:0.85em;'>¡Tienes todo!</span>"

    chips_tienes = "".join([
        f"<span style='background:#0d2a1a;border:1px solid #4ade8040;color:#4ade80;"
        f"padding:2px 8px;border-radius:12px;font-size:0.78em;margin:2px;display:inline-block;'>{x}</span>"
        for x in r["coincidencias"]
    ])

    return f"""
<div style="border:1px solid #1e1e30; border-radius:14px; margin-bottom:12px;
            overflow:hidden; background:#13131f;"
     onmouseenter="this.style.borderColor='#2e2e45'; this.style.boxShadow='0 4px 24px rgba(99,60,180,0.12)'"
     onmouseleave="this.style.borderColor='#1e1e30'; this.style.boxShadow='none'">

  <!-- CABECERA CLICKABLE -->
  <div onclick="
    var body = document.getElementById('body_{receta_id}');
    var arrow = document.getElementById('arrow_{receta_id}');
    if(body.style.display === 'none'){{
      body.style.display='block';
      arrow.style.transform='rotate(180deg)';
    }} else {{
      body.style.display='none';
      arrow.style.transform='rotate(0deg)';
    }}"
    style="padding:16px 20px; cursor:pointer; display:flex;
           justify-content:space-between; align-items:flex-start; gap:12px;">

    <div style="flex:1; min-width:0;">
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
        <span style="font-family:'Syne',sans-serif; font-size:1.05em;
                     font-weight:700; color:#e8e6f0;">{nombre}</span>
        <span style="background:{badge_color}22; color:{badge_color};
                     border:1px solid {badge_color}44; padding:2px 10px;
                     border-radius:20px; font-size:0.75em; font-weight:700;
                     font-family:'Syne',sans-serif;">{match:.0f}% match</span>
        <span style="background:{dif_color}18; color:{dif_color};
                     border:1px solid {dif_color}33; padding:2px 8px;
                     border-radius:20px; font-size:0.72em;">{dificultad}</span>
      </div>
      {barra}
      <div style="display:flex; gap:16px; margin-top:6px; color:#666; font-size:0.82em; flex-wrap:wrap;">
        <span>⏱ {tiempo} min</span>
        <span>🔥 {calorias} kcal</span>
        <span style="color:{'#f87171' if n_faltan > 0 else '#4ade80'};">
          {'❌ ' + str(n_faltan) + ' faltante' + ('s' if n_faltan != 1 else '') if n_faltan > 0 else '✅ Completa'}
        </span>
      </div>
    </div>

    <div id="arrow_{receta_id}"
         style="color:#444; font-size:0.9em; padding-top:4px;
                transition:transform 0.3s; flex-shrink:0;">▼</div>
  </div>

  <!-- CUERPO OCULTO -->
  <div id="body_{receta_id}" style="display:none; padding:16px 20px;
       border-top:1px solid #1e1e30; background:#0f0f1a;">

    <div style="display:flex; gap:24px; margin-bottom:16px; flex-wrap:wrap;">
      <div style="flex:1; min-width:160px;">
        <p style="font-family:'Syne',sans-serif; font-size:0.70em; font-weight:600;
                  letter-spacing:1px; color:#555; margin:0 0 8px;">TIENES</p>
        <div>{chips_tienes}</div>
      </div>
      <div style="flex:1; min-width:160px;">
        <p style="font-family:'Syne',sans-serif; font-size:0.70em; font-weight:600;
                  letter-spacing:1px; color:#555; margin:0 0 8px;">TE FALTA</p>
        <div>{chips_faltan}</div>
      </div>
    </div>

    <p style="font-family:'Syne',sans-serif; font-size:0.70em; font-weight:600;
              letter-spacing:1px; color:#555; margin:0 0 10px;">PREPARACIÓN</p>
    <ol style="margin:0; padding-left:20px; line-height:1.7;">
      {pasos}
    </ol>
  </div>
</div>
"""


# ──────────────────────────────────────────────
#  LÓGICA PRINCIPAL
# ──────────────────────────────────────────────

OPCIONES_TIEMPO = ["Todos", "< 15 min", "< 30 min", "< 60 min"]
OPCIONES_FALTAN = ["Todos", "0 faltan", "≤ 1 falta", "≤ 2 faltan"]


def aplicar_filtros(resultados, filtro_tiempo, filtro_faltan):
    if filtro_tiempo != "Todos":
        limites = {"< 15 min": 15, "< 30 min": 30, "< 60 min": 60}
        limite = limites[filtro_tiempo]
        resultados = [r for r in resultados if (r["receta"].get("tiempo_min") or 9999) < limite]

    if filtro_faltan != "Todos":
        max_f = {"0 faltan": 0, "≤ 1 falta": 1, "≤ 2 faltan": 2}[filtro_faltan]
        resultados = [r for r in resultados if
                      len([i for i in r["receta"]["ingredientes_clave"]
                           if i["item"].lower() not in [c.lower() for c in r["coincidencias"]]]) <= max_f]
    return resultados


def construir_cards(resultados, nombres_detectados):
    estado = {}
    nombres_recetas = []
    cards_html = ""

    for r in resultados:
        nombre = r["receta"]["nombre"].title()
        cards_html += tarjeta_receta(r)
        estado[nombre] = {
            "match": f"{r['porcentaje_match']*100:.0f}%",
            "ingredientes": ", ".join(nombres_detectados)
        }
        nombres_recetas.append(nombre)

    header = f"""
    <p style="font-family:'Syne',sans-serif; font-size:0.75em; font-weight:600;
              letter-spacing:1px; color:#555; margin:0 0 14px 2px;">
      {len(resultados)} RECETA{'S' if len(resultados) != 1 else ''} ENCONTRADA{'S' if len(resultados) != 1 else ''}
    </p>
    """
    return header + cards_html, estado, nombres_recetas


def analizar_nevera(imagen, n_recetas, min_conf, filtro_tiempo, filtro_faltan):
    conf_map = {"Bajo": 0.3, "Medio": 0.5, "Alto": 0.9}
    min_conf = conf_map.get(str(min_conf), 0.5)
    empty = ("", "<p style='color:#555;text-align:center;padding:40px;font-family:DM Sans,sans-serif;'>Los resultados aparecerán aquí</p>", {}, gr.update(choices=[], value=None))

    if imagen is None:
        return empty

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        imagen.save(tmp.name)
        tmp_path = tmp.name

    try:
        raw = detect_gemini(tmp_path)
        cleaned = clean_ingredients(raw, min_confidence=min_conf)
    except Exception as e:
        return "", f"<p style='color:#f87171;padding:20px;'>❌ Error con Gemini: {e}</p>", {}, gr.update(choices=[], value=None)
    finally:
        os.unlink(tmp_path)

    if not cleaned:
        return "", "<p style='color:#fbbf24;text-align:center;padding:40px;'>⚠️ No se detectaron ingredientes. Prueba con otra foto.</p>", {}, gr.update(choices=[], value=None)

    ingredientes_html = chips_ingredientes(cleaned)
    nombres = [i["name"] for i in cleaned]
    resultados = recomendar(nombres, recetas, vectorizer, tfidf_matrix, n=int(n_recetas))

    if not resultados:
        return ingredientes_html, "<p style='color:#555;text-align:center;padding:40px;'>⚠️ No encontramos recetas con esos ingredientes.</p>", {}, gr.update(choices=[], value=None)

    resultados = aplicar_filtros(resultados, filtro_tiempo, filtro_faltan)

    if not resultados:
        return ingredientes_html, "<p style='color:#555;text-align:center;padding:40px;'>🔍 Ninguna receta cumple los filtros.</p>", {}, gr.update(choices=[], value=None)

    cards_html, estado, nombres_recetas = construir_cards(resultados, nombres)
    return ingredientes_html, cards_html, estado, gr.update(choices=nombres_recetas, value=None)


def recomendar_manual(ingredientes_str, n_recetas, filtro_tiempo, filtro_faltan):
    if not ingredientes_str.strip():
        return "<p style='color:#fbbf24;padding:20px;'>⚠️ Escribe al menos un ingrediente.</p>"

    nombres = [i.strip().lower() for i in ingredientes_str.split(",") if i.strip()]
    resultados = recomendar(nombres, recetas, vectorizer, tfidf_matrix, n=int(n_recetas))

    if not resultados:
        return "<p style='color:#555;text-align:center;padding:40px;'>⚠️ No encontramos recetas con esos ingredientes.</p>"

    resultados = aplicar_filtros(resultados, filtro_tiempo, filtro_faltan)

    if not resultados:
        return "<p style='color:#555;text-align:center;padding:40px;'>🔍 Ninguna receta cumple los filtros.</p>"

    cards_html, _, _ = construir_cards(resultados, nombres)
    return cards_html


def guardar_rating(receta_seleccionada, gusto, relevancia, estado_resultados):
    if not receta_seleccionada:
        return "<span style='color:#fbbf24;font-family:DM Sans,sans-serif;'>⚠️ Selecciona una receta primero.</span>"
    if not gusto or not relevancia:
        return "<span style='color:#fbbf24;font-family:DM Sans,sans-serif;'>⚠️ Completa ambas valoraciones.</span>"

    info = estado_resultados.get(receta_seleccionada, {})

    with open(RATINGS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            receta_seleccionada,
            info.get("match", ""),
            info.get("ingredientes", ""),
            gusto,
            relevancia,
        ])

    return f"<span style='color:#4ade80;font-family:DM Sans,sans-serif;'>✅ Valoración guardada para <strong>{receta_seleccionada}</strong>. ¡Gracias!</span>"


# ──────────────────────────────────────────────
#  INTERFAZ GRADIO
# ──────────────────────────────────────────────

with gr.Blocks(title="🧊 Fridge Survival Guide", theme=gr.themes.Base(), css=CSS) as demo:

    gr.HTML("""
    <div style="text-align:center; padding:32px 8px 16px;">
      <div style="display:inline-block; position:relative;">
        <h1 style="
          font-family:'Syne',sans-serif;
          font-size:2.8em;
          font-weight:800;
          margin:0;
          letter-spacing:3px;
          color:#e8f4f8;
          text-shadow:
            0 0 20px rgba(120,200,255,0.6),
            0 0 40px rgba(100,180,255,0.3),
            0 2px 4px rgba(0,0,0,0.8);
          filter: drop-shadow(0 0 8px rgba(150,220,255,0.4));
        ">
          🧊 FRIDGE SURVIVAL GUIDE 🧊
        </h1>
        <p style="
          color:#7ab8d4;
          margin:8px 0 0;
          font-size:0.88em;
          letter-spacing:2px;
          font-family:'DM Sans',sans-serif;
          text-transform:uppercase;
          opacity:0.8;
        ">
          Fotografía tu nevera · Detectamos ingredientes · Te sugerimos recetas
        </p>
        <div style="
          position:absolute; bottom:-8px; left:50%; transform:translateX(-50%);
          width:60%; height:1px;
          background:linear-gradient(90deg, transparent, rgba(120,200,255,0.5), transparent);
        "></div>
      </div>
    </div>
    """)

    with gr.Tabs():

        # ── TAB 1: FOTO ──
        with gr.Tab("Analizar foto"):

            with gr.Row(equal_height=False):

                # COLUMNA IZQUIERDA — controles
                with gr.Column(scale=1, min_width=300):
                    imagen_input = gr.Image(
                        type="pil",
                        label="Foto de tu nevera",
                        height=240,
                    )
                    with gr.Row():
                        n_slider = gr.Slider(1, 10, value=5, step=1, label="Nº recetas")
                        conf_slider = gr.Radio(
                            choices=["Bajo", "Medio", "Alto"],
                            value="Medio",
                            label="Sensibilidad",
                        )
                    with gr.Row():
                        filtro_tiempo = gr.Dropdown(
                            choices=OPCIONES_TIEMPO, value="Todos",
                            label="⏱ Tiempo máx."
                        )
                        filtro_faltan = gr.Dropdown(
                            choices=OPCIONES_FALTAN, value="Todos",
                            label="❌ Ingredientes faltantes"
                        )
                    analizar_btn = gr.Button("Analizar nevera", variant="primary", size="lg")

                    gr.HTML("""
                    <div style="border-top:1px solid rgba(120,200,255,0.1); margin:16px 0 10px;padding-top:12px;">
                      <p style="font-family:'Syne',sans-serif; font-size:0.72em; font-weight:600;
                                letter-spacing:1px; color:#4a7a94; margin:0 0 12px;">⭐ VALORAR RECETA</p>
                    </div>
                    """)
                    estado_recetas = gr.State({})
                    dropdown_receta = gr.Dropdown(choices=[], label="Receta a valorar")
                    with gr.Row():
                        radio_gusto = gr.Radio(
                            choices=["👍 Me gusta", "👎 No me gusta"],
                            label="¿Te gusta?", scale=1
                        )
                        radio_relevancia = gr.Radio(
                            choices=["Usa lo que tengo", "Me faltan cosas"],
                            label="¿Es relevante?", scale=1
                        )
                    guardar_btn = gr.Button("Guardar valoración", variant="secondary")
                    rating_msg = gr.HTML("")

                # COLUMNA DERECHA — resultados
                with gr.Column(scale=1, min_width=340):
                    ingredientes_out = gr.HTML()
                    recetas_out = gr.HTML(
                        value="<p style='color:#444;text-align:center;padding:40px;font-family:DM Sans,sans-serif;'>Los resultados aparecerán aquí</p>")
            # Eventos
            analizar_btn.click(
                fn=analizar_nevera,
                inputs=[imagen_input, n_slider, conf_slider, filtro_tiempo, filtro_faltan],
                outputs=[ingredientes_out, recetas_out, estado_recetas, dropdown_receta],
            )
            guardar_btn.click(
                fn=guardar_rating,
                inputs=[dropdown_receta, radio_gusto, radio_relevancia, estado_recetas],
                outputs=rating_msg,
            )

        # ── TAB 2: MANUAL ──
        with gr.Tab("Ingredientes manuales"):
            gr.HTML("""
            <p style="color:#666; font-size:0.9em; margin:8px 0 16px; font-family:'DM Sans',sans-serif;">
              Escribe los ingredientes separados por comas para probar el recomendador sin foto.
            </p>
            """)
            with gr.Row():
                manual_input = gr.Textbox(
                    label="Ingredientes (separados por coma)",
                    placeholder="huevo, patata, queso, tomate...",
                    lines=2,
                    scale=3,
                )
                n_manual = gr.Slider(1, 10, value=5, step=1, label="Nº recetas", scale=1)
            with gr.Row():
                filtro_tiempo_m = gr.Dropdown(
                    choices=OPCIONES_TIEMPO, value="Todos", label="⏱ Tiempo máx."
                )
                filtro_faltan_m = gr.Dropdown(
                    choices=OPCIONES_FALTAN, value="Todos", label="❌ Ingredientes faltantes"
                )
            manual_btn = gr.Button("🍳 Ver recetas", variant="primary")
            manual_out = gr.HTML()

            manual_btn.click(
                fn=recomendar_manual,
                inputs=[manual_input, n_manual, filtro_tiempo_m, filtro_faltan_m],
                outputs=manual_out,
            )

# ──────────────────────────────────────────────
#  LANZAR
# ──────────────────────────────────────────────

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
    )

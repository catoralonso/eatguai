import gradio as gr
import tempfile
import os

from vision import detect_gemini, clean_ingredients
from recommender import cargar_recetas, init_vectorizer, recomendar

# ──────────────────────────────────────────────
#  CARGA DE DATOS (una sola vez)
# ──────────────────────────────────────────────

recetas = cargar_recetas("recetas_backend_proceso_ultra.json")
vectorizer, tfidf_matrix = init_vectorizer(recetas)

# ──────────────────────────────────────────────
#  LÓGICA PRINCIPAL
# ──────────────────────────────────────────────

def analizar_nevera(imagen, n_recetas, min_conf):
    if imagen is None:
        return "⚠️ Sube una imagen primero.", ""
   
    # Guardar imagen temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        imagen.save(tmp.name)
        tmp_path = tmp.name

    try:
        raw = detect_gemini(tmp_path, API_KEY)
        cleaned = clean_ingredients(raw, min_confidence=min_conf)
    except Exception as e:
        return f"❌ Error con Gemini: {e}", ""
    finally:
        os.unlink(tmp_path)

    if not cleaned:
        return "⚠️ No se detectaron ingredientes. Prueba con otra foto.", ""

    # Texto de ingredientes detectados
    ingredientes_txt = "\n".join(
        [f"{'🟢' if i['confidence'] >= 0.85 else '🟡' if i['confidence'] >= 0.65 else '🔴'} "
         f"{i['name']}  ({i['confidence']:.0%})"
         for i in cleaned]
    )

    # Recomendación
    nombres = [i["name"] for i in cleaned]
    resultados = recomendar(nombres, recetas, vectorizer, tfidf_matrix, n=int(n_recetas))

    if not resultados:
        return ingredientes_txt, "⚠️ No encontramos recetas con esos ingredientes.", ""

    # Formatear recetas
    recetas_txt = ""
    for r in resultados:
        rec = r["receta"]
        match = r["porcentaje_match"] * 100
        color = "#2d6a4f" if match == 100 else "#f4a261" if match >= 50 else "#e63946"
        coinciden = ", ".join(r["coincidencias"])
        faltan = [i["item"] for i in rec["ingredientes_clave"] 
                  if i["item"].lower() not in [c.lower() for c in r["coincidencias"]]]
        faltan_txt = ", ".join(faltan) if faltan else "ninguno"

        recetas_txt += f"""
---
### {rec['nombre'].title()}
**Match: {match:.0f}%** · ⏱ {rec.get('tiempo_min')} min · 🎯 {rec.get('dificultad').title()} · 🔥 {rec.get('calorias_aprox')} kcal

✅ **Tienes:** {coinciden}
❌ **Te falta:** {faltan_txt}

**Paso a paso:**

{"".join([f'- {paso}  ' + chr(10) for paso in rec.get('proceso_detallado', [])])}

"""
    return ingredientes_txt, recetas_txt


def recomendar_manual(ingredientes_str, n_recetas):
    if not ingredientes_str.strip():
        return "⚠️ Escribe al menos un ingrediente."

    nombres = [i.strip().lower() for i in ingredientes_str.split(",") if i.strip()]
    resultados = recomendar(nombres, recetas, vectorizer, tfidf_matrix, n=int(n_recetas))

    if not resultados:
        return "⚠️ No encontramos recetas con esos ingredientes."

    txt = ""
    for r in resultados:
        rec = r["receta"]
        match = r["porcentaje_match"] * 100
        badge = "🟢" if match == 100 else "🟡" if match >= 50 else "🔴"
        coinciden = ", ".join(r["coincidencias"])

        txt += f"{badge} **{rec['nombre'].upper()}** — Match: {match:.0f}%  ({r['n_coincidencias']} ingredientes)\n"
        txt += f"⏱ {rec.get('tiempo_min')} min  |  🎯 {rec.get('dificultad').title()}\n"
        txt += f"✅ Tienes: {coinciden}\n"
        txt += f"📋 {rec.get('proceso_corto')}\n"
        for paso in rec.get("proceso_detallado", []):
            txt += f"   {paso}\n"
        txt += "─" * 50 + "\n"

    return txt


# ──────────────────────────────────────────────
#  INTERFAZ GRADIO
# ──────────────────────────────────────────────

with gr.Blocks(title="🧊 Fridge Survival Guide") as demo:

    gr.Markdown("# 🧊 The Fridge Survival Guide")
    gr.Markdown("Sube una foto de tu nevera y te sugerimos recetas con lo que tienes.")

    with gr.Tabs():

        # ── TAB 1: FOTO ──
        with gr.Tab("📸 Analizar foto"):
            with gr.Row():
                with gr.Column(scale=1):
                    imagen_input = gr.Image(type="pil", label="Foto de tu nevera")            
                    with gr.Row():
                        n_slider = gr.Slider(1, 10, value=5, step=1, label="Nº recetas")
                        conf_slider = gr.Radio(
                            choices=[("Bajo — detecta todo aunque haya dudas", 0.3),
                                     ("Medio — ingredientes parcialmente visibles", 0.5),
                                     ("Alto — solo ingredientes muy claros", 0.9)],
                            value=0.5,
                            label="Sensibilidad de detección",
                        )
                    analizar_btn = gr.Button("🔍 Analizar nevera", variant="primary")

                with gr.Column(scale=1):
                    ingredientes_out = gr.Textbox(
                        label="🥕 Ingredientes detectados",
                        lines=10,
                        interactive=False,
                    )

            recetas_out = gr.Markdown(label="🍽️ Recetas recomendadas")

            analizar_btn.click(
                fn=analizar_nevera,
                inputs=[imagen_input, n_slider, conf_slider],
                outputs=[ingredientes_out, recetas_out],
            )

        # ── TAB 2: MANUAL ──
        with gr.Tab("✏️ Ingredientes manuales"):
            gr.Markdown("Escribe los ingredientes separados por comas para probar el recomendador sin foto.")
            with gr.Row():
                manual_input = gr.Textbox(
                    label="Ingredientes (separados por coma)",
                    placeholder="huevo, patata, queso, tomate...",
                    lines=2,
                )
                n_manual = gr.Slider(1, 10, value=5, step=1, label="Nº recetas")
            manual_btn = gr.Button("🍳 Ver recetas", variant="primary")
            manual_out = gr.Markdown()

            manual_btn.click(
                fn=recomendar_manual,
                inputs=[manual_input, n_manual],
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
        theme=gr.themes.Soft(),
    )

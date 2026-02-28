"""
Renderizado de UI con diseño 'Nevera de Noche'.
"""

from typing import List, Dict, Any, Optional
from config import COLORS, TYPO, CONFIG


class UIRenderer:
    """Renderiza componentes HTML profesionales."""
    
    @classmethod
    def get_base_styles(cls) -> str:
        """CSS base completo."""
        return f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@500;700&display=swap');
        
        :root {{
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
            
            --font-display: {TYPO.DISPLAY};
            --font-body: {TYPO.BODY};
            --font-data: {TYPO.DATA};
            --font-accent: {TYPO.ACCENT};
        }}
        
        /* Animaciones keyframes */
        @keyframes ambientPulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
        
        @keyframes scan {{
            0% {{ transform: translateY(-100%); }}
            100% {{ transform: translateY(100%); }}
        }}
        
        @keyframes shimmer {{
            0% {{ transform: translateX(-100%); }}
            100% {{ transform: translateX(100%); }}
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        @keyframes pulseGlow {{
            0%, 100% {{ box-shadow: 0 0 20px rgba(125, 211, 252, 0.2); }}
            50% {{ box-shadow: 0 0 30px rgba(125, 211, 252, 0.4); }}
        }}
        
        /* Clases utilitarias */
        .fridge-container {{
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: var(--font-body);
            min-height: 100vh;
            position: relative;
        }}
        
        .fridge-container::before {{
            content: '';
            position: fixed;
            inset: 0;
            background: 
                radial-gradient(ellipse at 20% 20%, rgba(125, 211, 252, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(20, 184, 166, 0.06) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
            animation: ambientPulse 8s ease-in-out infinite;
        }}
        
        .glass-panel {{
            background: rgba(19, 19, 31, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            box-shadow: 
                0 0 0 1px rgba(255, 255, 255, 0.02),
                0 20px 40px rgba(0, 0, 0, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.05);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}
        
        .glass-panel:hover {{
            border-color: var(--border-glow);
            box-shadow: 
                0 0 0 1px rgba(125, 211, 252, 0.1),
                0 20px 40px rgba(0, 0, 0, 0.5),
                0 0 30px rgba(125, 211, 252, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
        }}
        
        .text-hero {{
            font-family: var(--font-display);
            font-size: 2.8em;
            font-weight: 800;
            letter-spacing: -0.02em;
            text-shadow: 
                0 0 20px rgba(125, 211, 252, 0.5),
                0 0 40px rgba(125, 211, 252, 0.2);
            background: linear-gradient(135deg, #fff 0%, var(--ice-blue) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .text-label {{
            font-family: var(--font-accent);
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
        }}
        
        .fade-in {{
            animation: fadeIn 0.5s ease-out;
        }}
        
        .scanning-overlay {{
            position: absolute;
            inset: 0;
            background: linear-gradient(
                180deg,
                transparent 0%,
                rgba(125, 211, 252, 0.1) 50%,
                transparent 100%
            );
            animation: scan 2s linear infinite;
            pointer-events: none;
        }}
        </style>
        """
    
    @classmethod
    def render_header(cls, modo: str = "survival") -> str:
        config = CONFIG.get_mode(modo)
        color  = config["color"]
    
        return f"""
        <div style="text-align:center; padding:32px 20px 24px;">
            <h1 style="
                font-family:'Syne',sans-serif;
                font-size:2.8em;
                font-weight:800;
                margin:0;
                letter-spacing:3px;
                color:#e8f4f8;
                text-shadow:
                    0 0 20px rgba(120,200,255,0.6),
                    0 0 40px rgba(100,180,255,0.3);
            ">
                {config["icon"]} FRIDGE SURVIVAL GUIDE {config["icon"]}
            </h1>
            <p style="
                color:{color};
                margin:10px 0 0;
                font-size:0.88em;
                letter-spacing:2px;
                font-family:'DM Sans',sans-serif;
                text-transform:uppercase;
                opacity:0.85;
            ">
                {config["description"]}
            </p>
            <div style="
                width:60%; height:1px; margin:16px auto 0;
                background:linear-gradient(90deg, transparent, {color}80, transparent);
            "></div>
        </div>
        """  
    @classmethod
    def render_ingredients_grid(cls, ingredients: List[Any]) -> str:
        """Grid visual de ingredientes detectados."""
        if not ingredients:
            return ""
        
        cards = []
        for i, ing in enumerate(sorted(ingredients, key=lambda x: x.confidence, reverse=True)):
            emoji, cat_color = cls.get_ingredient_visual(ing.name)
            delay = f"animation-delay:{i*0.1}s;" if i < 6 else ""
            
            cards.append(f"""
            <div class="glass-panel" style="
                padding: 16px;
                text-align: center;
                position: relative;
                --confidence-color: {ing.color};
            ">
                <div style="
                    position: absolute;
                    top: 0; left: 0; right: 0; height: 3px;
                    background: {ing.color};
                    opacity: 0.8;
                    box-shadow: 0 0 8px {ing.color};
                "></div>
                <div style="font-size: 2.2em; margin-bottom: 8px; filter: drop-shadow(0 0 6px {ing.color}); animation:float 3s ease-in-out infinite;">
                    {emoji}
                </div>
                <div style="font-family: var(--font-body); font-size: 0.9em; color: var(--text-primary); margin-bottom: 4px;">
                    {ing.name.title()}
                </div>
                <div style="font-family: var(--font-data); font-size: 0.75em; color: var(--text-secondary);">
                    {ing.emoji} {ing.confidence:.0%}
                </div>
            </div>
            """)
        
        return f"""
        <div style="margin: 24px 0;">
            <div class="text-label" style="margin-bottom: 12px;">
                Ingredientes Detectados ({len(ingredients)})
            </div>
            <div style="
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
                gap: 12px;
            " class="fade-in">
                {''.join(cards)}
            </div>
        </div>
        """
    
    @classmethod
    def get_ingredient_visual(cls, name: str) -> tuple:
        """Retorna (emoji, color_de_categoría)"""
        categories = {
            "proteina": {
                "items": ["huevo", "huevos", "pollo", "carne", "pescado", "atún", "jamón", "tocino"],
                "emoji": "🥩",
                "color": "#f87171"
            },
            "lacteo": {
                "items": ["leche", "queso", "yogur", "mantequilla", "crema", "nata"],
                "emoji": "🥛",
                "color": "#60a5fa"
            },
            "vegetal": {
                "items": ["tomate", "lechuga", "cebolla", "ajo", "papa", "patata", "zanahoria", "pimiento"],
                "emoji": "🥬",
                "color": "#34d399"
            },
            "fruta": {
                "items": ["manzana", "plátano", "naranja", "limón", "fresa", "uva"],
                "emoji": "🍎",
                "color": "#fbbf24"
            },
            "grano": {
                "items": ["arroz", "pasta", "pan", "harina", "avena"],
                "emoji": "🌾",
                "color": "#d4d4d8"
            },
            "condimento": {
                "items": ["sal", "pimienta", "aceite", "vinagre", "salsa"],
                "emoji": "🧂",
                "color": "#a78bfa"
            }
        }
        
        name_lower = name.lower()
        for cat, data in categories.items():
            if any(item in name_lower for item in data["items"]):
                return data["emoji"], data["color"]
        
        return "🥘", "#94a3b8"
    
    @classmethod
    def render_empty_state(cls, message: str = "Los resultados aparecerán aquí", 
                           tipo: str = "default") -> str:
        """Empty state con icono temático y animación."""
        
        icons = {
            "default": "🧊",
            "no_results": "🔍❄️",
            "error": "⚠️🧊",
            "success": "✨🍽️"
        }
        icon = icons.get(tipo, "🧊")
        
        subtipos = {
            "default": "Sube una foto de tu nevera para comenzar",
            "no_results": "Prueba con otros ingredientes o filtros diferentes",
            "error": "Verifica la conexión e intenta de nuevo",
            "success": "¡Listo para cocinar!"
        }
        sub = subtipos.get(tipo, "")
        
        return f"""
        <div style="
            text-align:center; padding:60px 20px; color:var(--text-muted);
            font-family:var(--font-body); border:2px dashed var(--border-subtle);
            border-radius:16px; margin:20px 0; position:relative; overflow:hidden;
        ">
            <div style="
                font-size:3.5em; margin-bottom:20px; opacity:0.6;
                animation:float 6s ease-in-out infinite;
                filter:drop-shadow(0 0 20px rgba(125,211,252,0.2));
            ">
                {icon}
            </div>
            <p style="font-size:1.1em; margin:0 0 8px 0; color:var(--text-secondary);">
                {message}
            </p>
            <p style="font-size:0.85em; margin:0; opacity:0.6;">{sub}</p>
        </div>
        
        <style>
            @keyframes float {{
                0%, 100% {{ transform:translateY(0px); }}
                50% {{ transform:translateY(-10px); }}
            }}
        </style>
        """
    
    @classmethod
    def render_scanning(cls) -> str:
        """Efecto de escaneo moderno con puntos de carga."""
        return """
        <div style="
            position:relative; height:220px; background:var(--bg-secondary);
            border-radius:16px; overflow:hidden; display:flex; 
            flex-direction:column; align-items:center; justify-content:center;
            gap:20px;
        ">
            <div class="scanning-overlay"></div>
            
            <div style="display:flex; gap:6px;">
                <div style="
                    width:10px; height:10px; background:var(--ice-blue);
                    border-radius:50%; animation:dotPulse 1.4s infinite ease-in-out both;
                "></div>
                <div style="
                    width:10px; height:10px; background:var(--ice-blue);
                    border-radius:50%; animation:dotPulse 1.4s infinite ease-in-out both 0.2s;
                "></div>
                <div style="
                    width:10px; height:10px; background:var(--ice-blue);
                    border-radius:50%; animation:dotPulse 1.4s infinite ease-in-out both 0.4s;
                "></div>
            </div>
            
            <div style="text-align:center; z-index:1;">
                <div class="text-label" style="margin-bottom:6px;">Analizando nevera</div>
                <div style="font-family:var(--font-data); font-size:0.8em; color:var(--text-muted);">
                    Detectando ingredientes...
                </div>
            </div>
        </div>
        
        <style>
            @keyframes dotPulse {
                0%, 80%, 100% { transform:scale(0.6); opacity:0.4; }
                40% { transform:scale(1); opacity:1; box-shadow:0 0 10px var(--ice-blue); }
            }
        </style>
        """
    @classmethod
    def render_match_ring(cls, match: float, color: str, label: str) -> str:
        """Anillo circular de progreso con porcentaje."""
        circumference = 2 * 3.14159 * 16
        offset = circumference * (1 - match / 100)

        html = (
            f'<div style="position:relative; width:46px; height:46px; flex-shrink:0;">'
            f'<svg width="46" height="46" style="transform:rotate(-90deg);">'
            f'<circle cx="23" cy="23" r="16" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="3"/>'
            f'<circle cx="23" cy="23" r="16" fill="none" stroke="{color}" stroke-width="3"'
            f' stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"'
            f' stroke-linecap="round"'
            f' style="transition:stroke-dashoffset 1s ease-out; filter:drop-shadow(0 0 3px {color});"/>'
            f'</svg>'
            f'<div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center;">'
            f'<div style="font-family:var(--font-data); font-size:0.6em; font-weight:700; color:{color};">{match:.0f}%</div>'
            f'</div>'
            f'<div style="position:absolute; bottom:-14px; left:50%; transform:translateX(-50%); font-size:0.55em; color:{color}; white-space:nowrap; opacity:0.9;">'
            f'{label}'
            f'</div>'
            f'</div>'
        )
        return html        

    @classmethod
    def render_recipe_card(cls, rec: Any, modo: str = "survival") -> str:
        """Tarjeta completa de receta. Acepta objeto Recommendation."""
        from models import Recommendation
        import re

        recipe     = rec.receta
        match      = rec.porcentaje_match * 100
        mode_cfg   = CONFIG.get_mode(modo)
        color      = mode_cfg["color"]

        if match >= 95:
            match_color = COLORS.SUCCESS
            match_label = "Tienes todo ✓"
        elif match >= 75:
            match_color = "#a3e635"
            match_label = f"{match:.0f}% disponible"
        elif match >= 50:
            match_color = COLORS.WARNING
            match_label = f"{match:.0f}% disponible"
        else:
            match_color = COLORS.ERROR
            match_label = f"{match:.0f}% disponible"

        faltan     = [i.item for i in rec.ingredientes_faltantes]
        faltan_txt = ", ".join(faltan) if faltan else "ninguno 🎉"

        def limpiar_paso(p):
            return re.sub(r'^[\d]+[\.\)]\s*', '', p)

        pasos_html = "".join(
            f"<li style='margin-bottom:10px; padding-left:4px; "
            f"color:{COLORS.TEXT_SECONDARY}; line-height:1.6;'>"
            f"{limpiar_paso(p)}</li>"
            for p in recipe.proceso_detallado
        )

        chef_section = ""
        if modo == "chef" and mode_cfg.get("show_techniques"):
            tecnicas_html = ""
            if recipe.tecnicas:
                tecnicas_html = f"""
            <div style="margin-top:12px;">
                <span class="text-label">Técnicas</span>
                <div style="margin-top:6px; display:flex; flex-wrap:wrap; gap:6px;">
                    {"".join(f'<span style="background:{color}20; color:{color}; '
                             f'padding:3px 10px; border-radius:20px; font-size:0.8em;">'
                             f'{t}</span>' for t in recipe.tecnicas)}
                </div>
            </div>"""

            maridaje_html = ""
            if recipe.maridaje:
                maridaje_html = f"""
            <div style="margin-top:12px;">
                <span class="text-label">Maridaje</span>
                <p style="color:{COLORS.TEXT_SECONDARY}; margin:4px 0 0; font-size:0.9em;">
                    🍷 {recipe.maridaje}
                </p>
            </div>"""

            presentacion_html = ""
            if recipe.presentacion:
                presentacion_html = f"""
            <div style="margin-top:12px;">
                <span class="text-label">Presentación</span>
                <p style="color:{COLORS.TEXT_SECONDARY}; margin:4px 0 0; font-size:0.9em;">
                    🍽️ {recipe.presentacion}
                </p>
            </div>"""

            chef_notes_html = ""
            if recipe.chef_notes:
                chef_notes_html = f"""
            <div style="margin-top:12px; padding:12px; background:{color}10;
                        border-left:3px solid {color}; border-radius:0 8px 8px 0;">
                <span class="text-label">Nota del Chef</span>
                <p style="color:{COLORS.TEXT_PRIMARY}; margin:4px 0 0; font-size:0.9em;
                           font-style:italic;">
                    👨‍🍳 {recipe.chef_notes}
                </p>
            </div>"""

            chef_section = tecnicas_html + maridaje_html + presentacion_html + chef_notes_html

        recipe_id = recipe.nombre.replace(" ", "_").replace("/", "_").lower()

        return f"""
        <div class="glass-panel fade-in" style="margin-bottom:16px; padding:0; overflow:hidden;">
            <div style="height:3px; background:linear-gradient(90deg, {color}, {match_color});"></div>
            <div onclick="
                var b=document.getElementById('body_{recipe_id}');
                var a=document.getElementById('arrow_{recipe_id}');
                if(b.style.display==='none'){{b.style.display='block';a.textContent='▲';}}
                else{{b.style.display='none';a.textContent='▼';}}"
                style="padding:20px 24px; cursor:pointer; display:flex;
                       justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-family:{TYPO.DISPLAY}; font-size:1.15em;
                                font-weight:700; color:{COLORS.TEXT_PRIMARY};">
                        {recipe.nombre}
                    </div>
                    <div style="margin-top:6px; display:flex; gap:10px; flex-wrap:wrap;">
                        <span style="font-family:{TYPO.DATA}; font-size:0.75em;
                                     color:{COLORS.TEXT_MUTED};">
                            ⏱ {recipe.tiempo_min or '?'} min
                        </span>
                        <span style="font-family:{TYPO.DATA}; font-size:0.75em;
                                     color:{COLORS.TEXT_MUTED};">
                            📊 {(recipe.dificultad or 'N/A').title()}
                        </span>
                        <span style="font-family:{TYPO.DATA}; font-size:0.75em;
                                     color:{COLORS.TEXT_MUTED};">
                            🔥 {recipe.calorias_aprox or '?'} kcal
                        </span>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:16px;">
                {cls.render_match_ring(match, match_color, match_label)}
                    <span id="arrow_{recipe_id}" style="color:{COLORS.TEXT_MUTED};
                          font-size:0.8em;">▼</span>
                </div>
            </div>
            <div id="body_{recipe_id}" style="display:none; padding:0 24px 24px;
                 border-top:1px solid {COLORS.BORDER_SUBTLE};">
                <div style="margin-top:16px; padding:12px 16px;
                            background:{COLORS.BG_TERTIARY}; border-radius:10px;">
                    <span class="text-label">Te faltan</span>
                    <p style="margin:4px 0 0; font-size:0.9em;
                              color:{'#34d399' if not faltan else COLORS.WARNING};">
                        {faltan_txt}
                    </p>
                </div>
                <div style="margin-top:16px;">
                    <span class="text-label">Preparación</span>
                    <ol style="margin:10px 0 0; padding-left:20px;">
                        {pasos_html}
                    </ol>
                </div>
                {chef_section}
            </div>
        </div>
        """

    @classmethod
    def render_recipes_list(cls, recommendations: List[Any], modo: str = "survival") -> str:
        """Renderiza lista completa de recomendaciones."""
        if not recommendations:
            return cls.render_empty_state("No encontramos recetas con esos ingredientes")

        cards = "".join(cls.render_recipe_card(r, modo) for r in recommendations)
        return f"""
        <div class="fade-in">
            <div class="text-label" style="margin-bottom:16px;">
                🍽️ {len(recommendations)} recetas encontradas
            </div>
            {cards}
        </div>
        """

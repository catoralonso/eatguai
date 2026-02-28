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
        """Header principal con título animado."""
        config = CONFIG.MODES[modo]
        color = config["color"]
        
        return f"""
        <div class="fridge-container">
            <div style="text-align: center; padding: 40px 20px 30px; position: relative; z-index: 1;">
                <div style="display: inline-block; position: relative;">
                    <div style="
                        position: absolute;
                        inset: -20px;
                        background: radial-gradient(circle, {color}20 0%, transparent 70%);
                        filter: blur(20px);
                        animation: pulseGlow 3s ease-in-out infinite;
                    "></div>
                    <h1 class="text-hero" style="position: relative;">
                        {config["icon"]} FRIDGE SURVIVAL GUIDE {config["icon"]}
                    </h1>
                    <p style="
                        color: {color};
                        margin: 12px 0 0;
                        font-size: 0.9em;
                        letter-spacing: 3px;
                        font-family: var(--font-accent);
                        text-transform: uppercase;
                        opacity: 0.8;
                    ">
                        {config["description"]}
                    </p>
                </div>
            </div>
        </div>
        """
    
    @classmethod
    def render_ingredients_grid(cls, ingredients: List[Any]) -> str:
        """Grid visual de ingredientes detectados."""
        if not ingredients:
            return ""
        
        cards = []
        for ing in sorted(ingredients, key=lambda x: x.confidence, reverse=True):
            emoji = cls._get_ingredient_emoji(ing.name)
            
            cards.append(f"""
            <div class="glass-panel" style="
                padding: 16px;
                text-align: center;
                position: relative;
                --confidence-color: {ing.color};
            ">
                <div style="
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: {ing.color};
                    opacity: 0.6;
                "></div>
                <div style="font-size: 2em; margin-bottom: 8px; filter: drop-shadow(0 0 8px {ing.color});">
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
    def _get_ingredient_emoji(cls, name: str) -> str:
        """Mapeo de ingredientes a emojis."""
        mapping = {
            "huevo": "🥚", "huevos": "🥚",
            "leche": "🥛", "queso": "🧀", "yogur": "🥛",
            "pollo": "🍗", "carne": "🥩", "pescado": "🐟", "atún": "🐟",
            "tomate": "🍅", "lechuga": "🥬", "cebolla": "🧅", "ajo": "🧄",
            "papa": "🥔", "patata": "🥔", "zanahoria": "🥕",
            "arroz": "🍚", "pasta": "🍝", "pan": "🍞",
            "manzana": "🍎", "plátano": "🍌", "naranja": "🍊",
            "aceite": "🫒", "mantequilla": "🧈",
            "sal": "🧂", "azúcar": "🍬",
        }
        return mapping.get(name.lower(), "🥘")
    
    @classmethod
    def render_empty_state(cls, message: str = "Los resultados aparecerán aquí") -> str:
        """Estado vacío elegante."""
        return f"""
        <div style="
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
            font-family: var(--font-body);
            border: 2px dashed var(--border-subtle);
            border-radius: 16px;
            margin: 20px 0;
        ">
            <div style="font-size: 3em; margin-bottom: 16px; opacity: 0.5;">🧊</div>
            <p style="font-size: 1.1em; margin: 0;">{message}</p>
        </div>
        """
    
    @classmethod
    def render_scanning(cls) -> str:
        """Efecto de escaneo."""
        return """
        <div style="
            position: relative;
            height: 200px;
            background: var(--bg-secondary);
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        ">
            <div class="scanning-overlay"></div>
            <div style="text-align: center; z-index: 1;">
                <div style="font-size: 2em; margin-bottom: 12px;">🔍</div>
                <div class="text-label">Analizando nevera...</div>
                <div style="margin-top: 8px; font-family: var(--font-data); color: var(--ice-blue);">
                    Procesando imagen con Gemini AI
                </div>
            </div>
        </div>
        """
    @classmethod
        def render_recipe_card(cls, rec: Any, modo: str = "survival") -> str:
            """Tarjeta completa de receta. Acepta objeto Recommendation."""
            from models import Recommendation
            import re
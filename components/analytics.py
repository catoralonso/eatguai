"""
Persistencia y analytics de sesión.
"""

import os
import json
import csv
import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter

from config import CONFIG
from models import SessionState, Rating

logger = logging.getLogger(__name__)


class SimpleStore:
    """
    Almacenamiento simple en archivos CSV/JSON.
    Persiste mientras el VM de Vertex esté vivo.
    """
    
    def __init__(self):
        self.session = self._load_session()
        self._init_csv()
    
    def _load_session(self) -> SessionState:
        """Carga o crea sesión."""
        if os.path.exists(CONFIG.SESSION_FILE):
            try:
                with open(CONFIG.SESSION_FILE, 'r') as f:
                    data = json.load(f)
                    data['created_at'] = datetime.fromisoformat(data['created_at'])
                    data['last_activity'] = datetime.fromisoformat(data['last_activity'])
                    return SessionState(**data)
            except Exception as e:
                logger.warning(f"Error cargando sesión: {e}")
        
        return SessionState()
    
    def save_session(self):
        """Guarda sesión actual."""
        try:
            data = self.session.dict()
            data['created_at'] = data['created_at'].isoformat()
            data['last_activity'] = data['last_activity'].isoformat()
            
            with open(CONFIG.SESSION_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando sesión: {e}")
    
    def _init_csv(self):
        """Inicializa CSV de ratings."""
        if not os.path.exists(CONFIG.RATINGS_FILE):
            with open(CONFIG.RATINGS_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "receta", "match_pct",
                    "ingredientes", "gusto", "relevancia", "modo", "session_id"
                ])
    
    def add_rating(self, rating: Rating):
        """Agrega rating al CSV."""
        try:
            with open(CONFIG.RATINGS_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(rating.to_csv())
            self.session.ratings_enviados += 1
            self.save_session()
        except Exception as e:
            logger.error(f"Error guardando rating: {e}")
    
    def record_search(self, ingredients: List[str]):
        """Registra búsqueda."""
        self.session.busquedas_realizadas += 1
        for ing in ingredients:
            self.session.ingredientes_comunes[ing] = \
                self.session.ingredientes_comunes.get(ing, 0) + 1
        self.save_session()
    
    def get_summary(self) -> Dict[str, Any]:
        """Genera resumen para dashboard."""
        # Leer ratings
        ratings_count = 0
        try:
            with open(CONFIG.RATINGS_FILE, 'r') as f:
                ratings_count = sum(1 for _ in f) - 1  # Excluir header
        except:
            pass
        
        top_ing = sorted(
            self.session.ingredientes_comunes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "session_id": self.session.session_id,
            "busquedas": self.session.busquedas_realizadas,
            "ratings": ratings_count,
            "top_ingredientes": top_ing,
            "tiempo_activo": int((datetime.now() - self.session.created_at).total_seconds() / 60)
        }
    
    def export_message(self) -> str:
        """Mensaje de exportación."""
        return f"""
DATOS DE SESIÓN A EXPORTAR

Session ID: {self.session.session_id}
Inicio: {self.session.created_at.strftime('%Y-%m-%d %H:%M')}

Actividad:
- Búsquedas: {self.session.busquedas_realizadas}
- Ratings enviados: {self.session.ratings_enviados}

ARCHIVOS A DESCARGAR ANTES DE DESTRUIR EL VM:
1. {CONFIG.RATINGS_FILE}
2. {CONFIG.SESSION_FILE}
3. {CONFIG.LOG_FILE}

Comando para descargar:
gsutil cp data/* gs://tu-bucket/backup/  # Si tienes GCS
# o descarga manual desde el panel de archivos de Vertex
"""
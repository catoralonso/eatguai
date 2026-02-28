"""
Modelos Pydantic para validación de datos.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ConfidenceLevel(str, Enum):
    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"


class Difficulty(str, Enum):
    FACIL = "Fácil"
    MEDIA = "Media"
    DIFICIL = "Difícil"


class DetectedIngredient(BaseModel):
    """Ingrediente detectado por visión computacional."""
    
    name: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    raw_detection: Optional[str] = None
    category: Optional[str] = None
    
    @validator('name')
    def normalize(cls, v):
        return v.lower().strip()
    
    @property
    def emoji(self) -> str:
        if self.confidence >= 0.85:
            return "🟢"
        elif self.confidence >= 0.65:
            return "🟡"
        return "🔴"
    
    @property
    def color(self) -> str:
        from config import COLORS
        if self.confidence >= 0.85:
            return COLORS.SUCCESS
        elif self.confidence >= 0.65:
            return COLORS.WARNING
        return COLORS.ERROR


class RecipeIngredient(BaseModel):
    item: str
    quantity: Optional[float] = Field(None, alias="qty")
    unit: Optional[str] = None
    essential: bool = True
    category: Optional[str] = None

    class Config:
        populate_by_name = True 

class Recipe(BaseModel):
    receta_id: Optional[int] = None
    nombre: str
    categoria: Optional[str] = None
    tipo: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    ingredientes_clave: List[RecipeIngredient]
    ingredientes_base: List[str] = Field(default_factory=list)
    proceso_corto: Optional[str] = None
    proceso_detallado: List[str] = Field(default_factory=list)
    tiempo_min: Optional[int] = None
    dificultad: Optional[str] = None
    calorias_aprox: Optional[int] = None

    # Campos Chef Pro
    tecnicas: List[str] = Field(default_factory=list)
    maridaje: Optional[str] = None
    presentacion: Optional[str] = None
    chef_notes: Optional[str] = None

    @validator('nombre')
    def title_case(cls, v):
        return v.title()

class Recommendation(BaseModel):
    """Resultado de recomendación."""
    
    receta: Recipe
    porcentaje_match: float = Field(..., ge=0.0, le=1.0)
    coincidencias: List[str]
    ingredientes_faltantes: List[RecipeIngredient]
    score_total: float = 0.0
    
    @property
    def match_category(self) -> str:
        if self.porcentaje_match >= 0.95:
            return "perfect"
        elif self.porcentaje_match >= 0.75:
            return "high"
        elif self.porcentaje_match >= 0.50:
            return "medium"
        return "low"


class Rating(BaseModel):
    """Valoración de usuario."""
    
    timestamp: datetime = Field(default_factory=datetime.now)
    receta: str
    match_pct: str
    ingredientes_detectados: str
    gusto: str
    relevancia: str
    modo: str = "survival"
    session_id: Optional[str] = None
    
    def to_csv(self) -> List[str]:
        return [
            self.timestamp.isoformat(),
            self.receta,
            self.match_pct,
            self.ingredientes_detectados,
            self.gusto,
            self.relevancia,
            self.modo,
            self.session_id or ""
        ]


class SessionState(BaseModel):
    """Estado de sesión persistente."""
    
    session_id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    
    busquedas_realizadas: int = 0
    recetas_vistas: List[str] = Field(default_factory=list)
    ratings_enviados: int = 0
    ingredientes_comunes: Dict[str, int] = Field(default_factory=dict)
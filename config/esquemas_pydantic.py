from pydantic import BaseModel, Field
from typing import List, Optional

class DetalleFaseTrabajador(BaseModel):
    columna_fase: Optional[str] = Field(None, description="Columna de fase")
    fase_codigo: Optional[str] = Field(None, description="Código de fase (ej. CONS280, ADIC416)")
    descripcion_actividad: Optional[str] = Field(None, description="Descripción de la actividad")
    horas_hombre_fase: Optional[float] = Field(None, description="Horas hombre en esta fase")

class TrabajadorParteDiario(BaseModel):
    dni: Optional[str] = None
    apellidos_nombres: Optional[str] = None
    cargo: Optional[str] = None
    hora_ingreso: Optional[str] = None
    hora_salida: Optional[str] = None
    horas_normales: Optional[float] = None
    horas_60: Optional[float] = None
    horas_100: Optional[float] = None
    total_horas: Optional[float] = None
    detalles_fases: List[DetalleFaseTrabajador] = Field(default_factory=list)
    observacion: Optional[str] = "OK"

class ParteDiarioPaginaEsquema(BaseModel):
    fecha: Optional[str] = None
    frente: Optional[str] = None
    jefe_de_grupo: Optional[str] = None
    # Permitir que la lista sea flexible si una hoja viene con otro diseño
    trabajadores: List[TrabajadorParteDiario] = Field(default_factory=list)
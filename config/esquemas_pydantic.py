from pydantic import BaseModel, Field
from typing import List, Optional

class DetalleFaseTrabajador(BaseModel):
    columna_fase: Optional[str] = Field(None, description="Identificador de la columna de fase en la hoja (ej. 'Fase 01', 'Fase 02')")
    fase_codigo: Optional[str] = Field(None, description="Código exacto de la fase extraído de la cabecera superior (ej. 'CONS 280', 'ADIC416', 'NVCA 100')")
    descripcion_actividad: Optional[str] = Field(None, description="Descripción de la actividad correspondiente a esa fase según la tabla superior del formato")
    horas_hombre_fase: Optional[float] = Field(None, description="Horas hombre exactas asignadas en esta fase para este trabajador")

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
    detalles_fases: List[DetalleFaseTrabajador] = Field(default_factory=list, description="Desglose por cada fase y actividad en la que laboró el trabajador")
    observacion: Optional[str] = "OK"

class ParteDiarioPaginaEsquema(BaseModel):
    fecha: Optional[str] = None
    frente: Optional[str] = None
    jefe_de_grupo: Optional[str] = None
    trabajadores: List[TrabajadorParteDiario] = Field(default_factory=list)
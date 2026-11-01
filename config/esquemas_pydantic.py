from pydantic import BaseModel, Field
from typing import List, Optional

class DetalleFaseTrabajador(BaseModel):
    columna_fase: Optional[str] = Field(None, description="Columna de fase")
    fase_codigo: Optional[str] = Field(None, description="Código de fase (ej. CONS280, ADIC416)")
    descripcion_actividad: Optional[str] = Field(None, description="Descripción de la actividad")
    horas_hombre_fase: Optional[float] = Field(None, description="Horas hombre en esta fase")

class TrabajadorParteDiario(BaseModel):
    dni: Optional[str] = Field(None, description="DNI del trabajador")
    apellidos_nombres: Optional[str] = Field(None, description="Apellidos y nombres")
    cargo: Optional[str] = Field(None, description="Cargo del trabajador")
    hora_ingreso: Optional[str] = Field(None, description="Hora de ingreso")
    hora_salida: Optional[str] = Field(None, description="Hora de salida")
    horas_normales: Optional[float] = Field(None, description="Horas normales (H.N.)")
    horas_60: Optional[float] = Field(None, description="Horas al 60%")
    horas_100: Optional[float] = Field(None, description="Horas al 100%")
    total_horas: Optional[float] = Field(None, description="Total de horas")
    detalles_fases: List[DetalleFaseTrabajador] = Field(default_factory=list, description="Desglose por fase")
    observacion: Optional[str] = Field("OK", description="Observación o estado del registro")

class ParteDiarioPaginaEsquema(BaseModel):
    fecha: Optional[str] = Field(None, description="Fecha del parte diario")
    frente: Optional[str] = Field(None, description="Frente de obra")
    jefe_de_grupo: Optional[str] = Field(None, description="Jefe de grupo")
    # Usamos default_factory=list para evitar que falle si la IA no detecta filas en algún formato distinto
    trabajadores: List[TrabajadorParteDiario] = Field(default_factory=list, description="Lista de trabajadores extraídos")
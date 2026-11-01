from typing import List, Optional
from pydantic import BaseModel, Field

class RegistroTrabajadorPlano(BaseModel):
    pagina: Optional[int] = Field(default=1, description="Número de página de origen dentro del PDF")
    fecha: str = Field(description="Fecha en formato DD/MM/YYYY")
    turno: str = Field(description="Turno (DIA / NOCHE)")
    proyecto: str = Field(description="Proyecto u Obra")
    sector: str = Field(description="Sector u Obra")
    frente: str = Field(description="Frente de trabajo")
    jefe_grupo: str = Field(description="Jefe de grupo o capataz")
    dni_jefe: Optional[str] = Field(default="", description="DNI del Jefe de Grupo si figura")
    nombres_apellidos: str = Field(description="Apellidos y Nombres del trabajador")
    dni: str = Field(description="DNI o documento del trabajador")
    hh: float = Field(description="Total Horas Hombre (HH)")
    fase: str = Field(description="Código de la fase asignada (ej. LABA-100, VIGIA100, MANT100, etc.)")
    control_actividad: str = Field(description="Descripción del trabajo correspondiente a la fase registrada")
    hora_ingreso: str = Field(description="Hora de ingreso (ej. 18:00)")
    hora_salida: str = Field(description="Hora de salida (ej. 06:00)")
    hn: float = Field(description="Horas Normales (H.N.)")
    horas_60: float = Field(default=0.0, description="Horas al 60%")
    horas_100: float = Field(default=0.0, description="Horas al 100%")
    total_horas: float = Field(description="Total Horas Reales")
    estado: str = Field(description="'OK' si todo coincide perfectamente, 'REVISAR' si hay descuadres o ilegibilidad")
    observaciones: Optional[str] = Field(default="", description="Detalle de la observación si el estado es REVISAR")

class ParteDiarioPaginaEsquema(BaseModel):
    registros: List[RegistroTrabajadorPlano] = Field(description="Lista de trabajadores registrados en esta página")
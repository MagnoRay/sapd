import time
import logging
from PIL import Image
from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY, MODEL_NAME
from config.esquemas_pydantic import ParteDiarioPaginaEsquema

logger = logging.getLogger(__name__)

def procesar_pagina_parte_diario(
    imagen: Image.Image, 
    nombre_archivo: str = "documento.pdf",
    max_reintentos: int = 4,
    espera_inicial: int = 10
) -> ParteDiarioPaginaEsquema:
    """
    Procesa una página del parte diario con reintento automático ante saturación (429) o errores temporales (503).
    """
    if not GEMINI_API_KEY:
        raise ValueError("No se encontró la variable GEMINI_API_KEY en el archivo .env")

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt_instrucciones = """
    Eres un auditor contable experto en Control de Asistencia del Régimen Construcción Civil.
    Analiza esta página del 'PARTE DIARIO MANO DE OBRA'.

    REGLA DE MAPEO ACTIVIDAD vs FASE:
    - En la cabecera existe la sección 'DESCRIPCION DE LOS TRABAJOS' con números 1, 2, 3, 4 y sus 'FASE' o códigos asociados.
    - La Actividad 1 mapea a Fase 01, Actividad 2 a Fase 02, Actividad 3 a Fase 03, Actividad 4 a Fase 04.
    - Para cada trabajador con registro de horas en la tabla:
      1. Identifica en qué columna de Fase (Fase 01..05) tiene sus horas anotadas.
      2. Asigna en 'fase' el código de la fase correspondiente (ej. VIGIA-100, LABA-100, MANT-100).
      3. Asigna en 'control_actividad' la Descripción del trabajo exacta asociada a esa Actividad/Fase.

    CAMPOS A EXTRAER POR CADA TRABAJADOR:
    - fecha: Fecha del reporte (DD/MM/YYYY)
    - turno: DIA / NOCHE
    - proyecto: Nombre del Proyecto / Obra (ej. CONSTRUCCION DE BOTADERO PIONERO)
    - sector: Sector u Obra
    - frente: Frente registrado
    - jefe_grupo: Nombre del Jefe de Grupo
    - dni_jefe: DNI del Jefe de Grupo si aparece
    - nombres_apellidos: Apellidos y nombres completos del trabajador
    - dni: DNI del trabajador
    - hh: Horas Hombre acumuladas / Total HH
    - fase: Código de la Fase asignada
    - control_actividad: Descripción de la Actividad
    - hora_ingreso: Hora de ingreso (HH:MM)
    - hora_salida: Hora de salida (HH:MM)
    - hn: Horas Normales (H.N.)
    - horas_60: Horas 60%
    - horas_100: Horas 100%
    - total_horas: Total de horas reales
    - estado: 'OK' si coinciden las horas y lecturas; 'REVISAR' si hay diferencias, firmas faltantes o ilegibilidad.
    - observaciones: Explicación si el estado es REVISAR.
    """

    for intento in range(1, max_reintentos + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[imagen, prompt_instrucciones],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ParteDiarioPaginaEsquema,
                    temperature=0.1,
                    max_output_tokens=8192,
                )
            )
            
            resultado = response.parsed
            print(f"-> Archivo {nombre_archivo}: Se extrajeron {len(resultado.registros)} registros de trabajadores.")
            return resultado

        except Exception as e:
            error_str = str(e)
            es_cuota_o_saturacion = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str or "UNAVAILABLE" in error_str

            if es_cuota_o_saturacion and intento < max_reintentos:
                tiempo_espera = espera_inicial * intento
                logger.warning(
                    f"[Límite de Cuota / Saturación] Intento {intento}/{max_reintentos} en {nombre_archivo}. "
                    f"Pausando {tiempo_espera}s para respetar la cuota de la API..."
                )
                time.sleep(tiempo_espera)
            else:
                logger.error(f"Error procesando página con Gemini (Intento {intento}): {error_str}")
                raise RuntimeError(f"Error de análisis con la IA: {error_str}")
import io
import time
from PIL import Image
from google import genai
from google.genai import types

# Importar la configuración que ya lee st.secrets en Streamlit Cloud y .env en local
from config.settings import GEMINI_API_KEY, MODEL_NAME
from config.esquemas_pydantic import ParteDiarioPaginaEsquema

def obtener_cliente_genai():
    """Inicializa el cliente de Gemini utilizando la API Key provista por settings.py."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "No se encontró la clave de API (GEMINI_API_KEY). "
            "Asegúrate de haberla configurado en los Secrets de Streamlit Cloud o en el archivo .env local."
        )
    return genai.Client(api_key=GEMINI_API_KEY)

def procesar_pagina_parte_diario(imagen_pil: Image.Image, nombre_archivo: str = "Página", intentos_max: int = 3):
    """
    Procesa una sola página (imagen) con Gemini y la estructura según ParteDiarioPaginaEsquema.
    Aplica reintentos si ocurren errores de cuota (429), servidores ocupados (503) o truncamiento de respuesta.
    """
    client = obtener_cliente_genai()

    # PROMPT ACTUALIZADO: Instrucción estricta para desglosar múltiples fases y horas por trabajador
    prompt = """
    Analiza la imagen adjunta correspondiente a un Parte Diario de Asistencia de personal de construcción.
    
    INSTRUCCIÓN CRÍTICA DE EXTRACCIÓN Y ASOCIACIÓN PLANA:
    1. **ENCABEZADO DE LA PÁGINA:** Extrae la fecha, turno, proyecto, sector, frente, jefe de grupo y DNI del jefe si figura.
    2. **TABLA SUPERIOR (ACTIVIDADES Y FASES):** Lee la lista superior de trabajos donde cada Actividad (1, 2, 3, 4...) tiene un Código de Fase exacto (ej. 'NU CA 100', 'Cons 280', 'ADIC416') y su Descripción textual del trabajo.
    3. **MATRIZ INFERIOR (TRABAJADORES Y HORAS POR FASE):** 
       - Las columnas de horas de la matriz inferior corresponden ordenadamente de izquierda a derecha a las actividades superiores (Fase 01 = Act. 1, Fase 02 = Act. 2, Fase 03 = Act. 3, Fase 04 = Act. 4).
       - **REGLA DE REGISTROS MÚLTIPLES:** Por cada trabajador, si registra horas en más de una columna de fase (por ejemplo, tiene horas en Fase 01 y horas en Fase 02), **debes generar un registro independiente (una fila por cada fase)** en la lista de `registros`.
       - Cada fila generada para el trabajador debe contener:
         * Sus datos personales (dni, nombres_apellidos, cargo, ingreso, salida, H.N., 60%, 100%, total_horas).
         * El **código de fase** y la **descripción de la actividad** exacta que le corresponde según la columna de fase analizada (respetando estrictamente el orden superior).
         * Las **hh** (horas de esa fase específica).
    
    Verifica que los cálculos sean coherentes. Si todo es correcto, asigna el estado 'OK'; si hay discrepancias o ilegibilidad, asigna 'REVISAR' en el estado con su respectiva observación.
    """

    for intento in range(1, intentos_max + 1):
        try:
            # Convertir imagen PIL a Bytes
            buffer = io.BytesIO()
            imagen_pil.save(buffer, format="JPEG", quality=85)
            bytes_imagen = buffer.getvalue()

            # Configuración de respuesta estructurada en formato JSON
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ParteDiarioPaginaEsquema,
                temperature=0.1
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    types.Part.from_bytes(data=bytes_imagen, mime_type="image/jpeg"),
                    prompt
                ],
                config=config
            )

            # Validar y deserializar usando Pydantic
            if response.text:
                return ParteDiarioPaginaEsquema.model_validate_json(response.text)
            else:
                raise ValueError("La respuesta de la IA llegó vacía.")

        except Exception as e:
            mensaje_error = str(e)
            # Manejo de cuota (429) o servidores ocupados (503 / UNAVAILABLE) con reintento automático
            if "429" in mensaje_error or "RESOURCE_EXHAUSTED" in mensaje_error or "503" in mensaje_error or "UNAVAILABLE" in mensaje_error:
                if intento < intentos_max:
                    time.sleep(6 * intento)
                    continue
            if intento == intentos_max:
                raise RuntimeError(f"Error procesando {nombre_archivo}: {mensaje_error}")
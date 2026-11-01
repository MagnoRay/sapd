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
    
    INSTRUCCIÓN CRÍTICA DE ASOCIACIÓN Y VALIDACIÓN CRUZADA:
    1. **TABLA SUPERIOR (ACTIVIDADES Y FASES):** Lee rigurosamente la sección superior de trabajos donde cada Actividad tiene un número ordenado (1, 2, 3, 4), un Código de Fase exacto (ej. 'NVCA 100', 'CONS 280', 'ADIC 416') y su Descripción textual.
    2. **MATRIZ INFERIOR (CONTROL DE HORAS):** En la tabla de trabajadores, las columnas de horas están numeradas de izquierda a derecha como:
       - Columna 1 de Fase (corresponde exactamente a la Actividad 1 superior).
       - Columna 2 de Fase (corresponde exactamente a la Actividad 2 superior).
       - Columna 3 de Fase (corresponde exactamente a la Actividad 3 superior).
       - Columna 4 de Fase (corresponde exactamente a la Actividad 4 superior).
    3. **REGLA ESTRICTA DE EXTRACCIÓN:** Para cada trabajador, verifica cuidadosamente celda por celda en qué columna de fase tiene horas registradas (> 0):
       - Si tiene horas en la primera columna de fase, asígnale obligatoriamente el código de fase y la descripción de la **Actividad 1**.
       - Si tiene horas en la segunda columna de fase, asígnale obligatoriamente el código de fase y la descripción de la **Actividad 2**.
       - Si tiene horas en la tercera columna de fase, asígnale obligatoriamente el código de fase y la descripción de la **Actividad 3**.
       - Si tiene horas en la cuarta columna de fase, asígnale obligatoriamente el código de fase y la descripción de la **Actividad 4**.
    4. Genera una fila independiente en 'detalles_fases' por cada columna donde el trabajador tenga horas, respetando fielmente este orden posicional de columnas. No cruces ni inviertas las descripciones.
    
    Extrae también con precisión la fecha, frente, jefe de grupo, DNI, nombres, cargo, horas de ingreso, salida, H.N., 60%, 100% y total de horas.
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
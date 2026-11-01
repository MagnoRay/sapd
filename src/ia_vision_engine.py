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
    
    INSTRUCCIÓN CRÍTICA DE ASOCIACIÓN DINÁMICA (ACTIVIDAD - FASE - DESCRIPCIÓN - HORAS):
    1. En la parte superior de la hoja existe una tabla de "DESCRIPCION DE LOS TRABAJOS" donde cada Actividad (1, 2, 3, 4...) está enlazada inequívocamente a un Código de Fase (ej. 'CONS 280', 'ADIC416', 'NVCA 100') y a su respectiva descripción textual del trabajo.
    2. En la parte inferior, cada trabajador posee una matriz de control de horas dividida por columnas de fases (Fase 01, Fase 02, Fase 03, etc.).
    3. Debes cruzar la información de manera rigurosa: si un trabajador tiene horas en una columna de fase específica, busca arriba cuál es el código de fase exacto y su descripción de trabajo correspondiente, y asígnalos conjuntamente en 'detalles_fases'.
    4. Genera una fila o elemento independiente por cada fase en la que el trabajador registre horas mayores a cero, garantizando que la descripción y el código de fase correspondan exactamente a lo indicado en la cabecera superior del formato, sin importar si cambia la posición o el diseño en este documento.
    
    Extrae también la fecha, frente, jefe de grupo, DNI, nombres, cargo, horas de ingreso, salida, H.N., 60%, 100% y total de horas. Si encuentras alguna incongruencia, marca el estado 'REVISAR' en la observación.
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
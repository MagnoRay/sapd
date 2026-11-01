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
    
    INSTRUCCIÓN CRÍTuCA DE ASOCIACIÓN EXACTA (ACTIVIDAD - FASE - DESCRIPCIÓN - HORAS):
    1. En la parte superior izquierda existe una tabla de "DESCRIPCION DE LOS TRABAJOS" donde cada Actividad está enumerada exactamente así:
       - Actividad 1 -> tiene su respectiva Descripción y su Código de Fase.
       - Actividad 2 -> tiene su respectiva Descripción y su Código de Fase.
       - Actividad 3 -> tiene su respectiva Descripción y su Código de Fase.
       - Actividad 4 -> tiene su respectiva Descripción y su Código de Fase.
    2. En la parte inferior, la matriz de control de horas por trabajador se divide en columnas numeradas:
       - 'Fase 01' corresponde estrictamente a la Actividad 1.
       - 'Fase 02' corresponde estrictamente a la Actividad 2.
       - 'Fase 03' corresponde estrictamente a la Actividad 3.
       - 'Fase 04' corresponde estrictamente a la Actividad 4.
    3. REGLA DE EXTRACCIÓN: Para cada trabajador, revisa qué valor de horas tiene en cada columna ('Fase 01', 'Fase 02', etc.). Si tiene horas en dicha columna (por ejemplo, 10 horas en Fase 02), debes generar una fila/detalle independiente que contenga:
       - El código de fase exacto de la Actividad 2 (ej. CONS280).
       - La descripción textual exacta de la Actividad 2 (ej. Vaciado de loza).
       - Las horas exactas registradas en esa fase.
    4. No mezcles las descripciones ni asignes fases incorrectas; respeta rigurosamente el índice numérico (Fase 01 con Act. 1, Fase 02 con Act. 2, etc.).
    
    Extrae también la fecha, frente, jefe de grupo, DNI, nombres, cargo, horas de ingreso, salida, H.N., 60%, 100% y total de horas. Si hay alguna discrepancia, asigna el estado 'REVISAR' en la observación.
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
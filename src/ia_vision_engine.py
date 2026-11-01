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
    
    INSTRUCCIÓN CRÍTICA DE ASOCIACIÓN EXACTA (MAPEO ENTRE TABLA SUPERIOR E INFERIOR):
    1. En la parte superior izquierda de la hoja hay una tabla de "DESCRIPCION DE LOS TRABAJOS" numerada por filas de Actividad (Act. 1, Act. 2, Act. 3, Act. 4). Cada una tiene:
       - Su respectivo **Código de Fase** (ej. 'NVCA 100', 'CONS 280', 'ADIC 416').
       - Su respectiva **Descripción del Trabajo** (ej. "Perfilado de talud y loza", "Vaciado de loza", "Parada de Seguridad").
    2. En la parte inferior, la tabla de trabajadores tiene columnas de control de horas etiquetadas como **Fase 01, Fase 02, Fase 03, Fase 04, Fase 05**.
    3. REGLA DE CORRESPONDENCIA DE COLUMNAS: 
       - La columna inferior 'Fase 01' corresponde a la Actividad de la fila 1 superior.
       - La columna inferior 'Fase 02' corresponde a la Actividad de la fila 2 superior.
       - La columna inferior 'Fase 03' corresponde a la Actividad de la fila 3 superior.
       - La columna inferior 'Fase 04' corresponde a la Actividad de la fila 4 superior.
    4. EXTRACCIÓN POR TRABAJADOR: Para cada trabajador, revisa cada columna de fase (Fase 01, Fase 02, etc.). Si el trabajador tiene horas asignadas en dicha columna (por ejemplo, 10 horas en Fase 02 y 1 hora en Fase 03):
       - Genera un registro independiente en 'detalles_fases' para la Fase 02 con el código y la descripción exacta que le pertenece a la Actividad 2 de la tabla superior.
       - Genera otro registro independiente para la Fase 03 con el código y la descripción exacta que le pertenece a la Actividad 3 de la tabla superior.
    
    Extrae rigurosamente la fecha, frente, jefe de grupo, DNI, nombres, cargo, horas de ingreso, salida, H.N., 60%, 100% y total de horas. Si encuentras celdas vacías o ambiguas en las fases, omítelas y procesa únicamente las que tengan horas reales mayores a cero.
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
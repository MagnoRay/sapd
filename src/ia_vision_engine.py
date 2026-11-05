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
    
    INSTRUCCIÓN CRÍTICA DE EXTRACCIÓN CONDICIONAL (SOLO FASES CON HORAS > 0):
    1. **TABLA SUPERIOR (ACTIVIDADES Y FASES):** Identifica la lista de trabajos arriba a la izquierda. Cada Actividad tiene un número ordenado (1, 2, 3, 4), un Código de Fase exacto (ej. 'NU CA 100', 'CONS 280', 'ADIC 416') y una Descripción textual.
    2. **MATRIZ INFERIOR (CONTROL DE HORAS POR FASE):** En la tabla de trabajadores, las columnas de horas están numeradas de izquierda a derecha:
       - Fase 01 = Corresponde exclusivamente a la Actividad 1.
       - Fase 02 = Corresponde exclusivamente a la Actividad 2.
       - Fase 03 = Corresponde exclusivamente a la Actividad 3.
       - Fase 04 = Corresponde exclusivamente a la Actividad 4.
    3. **REGLA DE FILTRADO ESTRICTO (¡MUY IMPORTANTE!):** 
       - **SOLO** debes generar un registro (una fila en la lista) si el trabajador tiene **horas mayores a cero (> 0)** en esa columna de fase específica.
       - Si una fase está vacía o tiene 0 horas para ese trabajador, **NO LA GENERES**.
       - Por ejemplo, si un trabajador solo laboró en la *Fase 04*, debes generar **únicamente 1 registro** que contenga el código de fase y la descripción exacta que le pertenece a la **Actividad 4**. No agregues filas de las otras fases si no tienen horas.
    4. **LECTURA ESTRICTA DE DNI Y ESTADOS:**
       - Extrae los números del DNI tal como figuran impresos en el documento físico. 
       - Si el DNI tiene menos de 8 dígitos (por error humano de llenado en obra), extráelo exactamente tal cual, **bajo ninguna circunstancia inventes ni agregues ceros a la izquierda**.
       - Si detectas que un DNI está incompleto o ilegible, coloca obligatoriamente en el campo **estado**: 'REVISAR' y en **observaciones**: 'DNI incompleto en origen'. Si tiene sus 8 dígitos correctos, asigna 'OK'.
    5. Extrae con absoluta precisión la fecha, turno, proyecto, sector, frente, jefe de grupo, DNI del trabajador, nombres, cargo, horas de ingreso, salida, H.N., 60%, 100% y total de horas.
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
import io
import logging
from typing import List, Union
from PIL import Image
import pypdfium2 as pdfium

logger = logging.getLogger(__name__)

def convertir_pdf_a_imagenes(
    origen_pdf: Union[str, bytes], 
    scale: float = 3.0
) -> List[Image.Image]:
    """
    Convierte un PDF (en ruta o bytes) a una lista de imágenes PIL utilizando pypdfium2,
    evitando la necesidad de instalar dependencias externas como Poppler en Windows.

    Args:
        origen_pdf (str | bytes): Archivo PDF en bytes leídos desde Streamlit o ruta local.
        scale (float): Factor de escala para definir la resolución (3.0 ofrece excelente calidad para OCR/IA).

    Returns:
        List[Image.Image]: Lista de imágenes correspondientes a cada página.
    """
    try:
        # pypdfium2 acepta tanto rutas (str) como objetos binarios o buffers (bytes / io.BytesIO)
        if isinstance(origen_pdf, bytes):
            pdf = pdfium.PdfDocument(io.BytesIO(origen_pdf))
        else:
            pdf = pdfium.PdfDocument(origen_pdf)

        imagenes = []
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            imagenes.append(pil_image)
        
        logger.info(f"Se convirtieron {len(imagenes)} página(s) de PDF a imagen con pypdfium2 con éxito.")
        return imagenes

    except Exception as e:
        logger.error(f"Error al convertir el PDF con pypdfium2: {str(e)}")
        raise RuntimeError(
            f"No se pudo procesar el archivo PDF. Asegúrate de que no esté dañado o protegido. Detalle: {str(e)}"
        )

def cargar_imagen_directa(origen_imagen: Union[str, bytes]) -> Image.Image:
    """
    Carga y valida una imagen directa (JPG, PNG, JPEG) en un objeto PIL Image.
    """
    try:
        if isinstance(origen_imagen, bytes):
            img = Image.open(io.BytesIO(origen_imagen))
        else:
            img = Image.open(origen_imagen)
        
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        return img
    except Exception as e:
        logger.error(f"Error al cargar la imagen: {str(e)}")
        raise ValueError(f"No se pudo cargar la imagen suministrada. Detalle: {str(e)}")
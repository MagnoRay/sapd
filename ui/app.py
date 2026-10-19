import time
import streamlit as st
from src.convertidor_pdf import convertir_pdf_a_imagenes, cargar_imagen_directa
from src.ia_vision_engine import procesar_pagina_parte_diario
from src.gestor_excel import generar_excel_asistencia

st.set_page_config(
    page_title="Control de Asistencia - Régimen C. Civil",
    page_icon="👷‍♂️",
    layout="wide"
)

def main():
    st.title("👷‍♂️ Sistema Automatizado de Partes Diarios - Régimen C. Civil")
    st.markdown("""
    Sube los archivos PDF o imágenes de los Partes Diarios. El sistema extraerá de forma continua y segura los datos de cada página, consolidando **todos los trabajadores en un único Excel plano de 20 columnas**.
    """)

    archivos_subidos = st.file_uploader(
        "Selecciona los archivos PDF o Imágenes",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if archivos_subidos:
        st.success(f"Se han cargado {len(archivos_subidos)} archivo(s).")

        if st.button("🚀 Procesar Documentos con IA", type="primary"):
            todos_los_registros = []
            paginas_a_procesar = []

            for archivo in archivos_subidos:
                st.write(f"Cargando y preparando: **{archivo.name}**...")
                try:
                    archivo_bytes = archivo.read()
                    if archivo.name.lower().endswith(".pdf"):
                        imagenes = convertir_pdf_a_imagenes(archivo_bytes)
                    else:
                        imagenes = [cargar_imagen_directa(archivo_bytes)]

                    for p_idx, img in enumerate(imagenes):
                        num_pagina = p_idx + 1
                        nombre_pag = f"{archivo.name} (Pág. {num_pagina})"
                        paginas_a_procesar.append((nombre_pag, img, num_pagina))

                except Exception as e:
                    st.error(f"Error cargando {archivo.name}: {str(e)}")

            if paginas_a_procesar:
                st.info(f"⚡ Procesando {len(paginas_a_procesar)} página(s) secuencialmente para cumplir con la cuota de la API...")
                barra_progreso = st.progress(0)
                total_paginas = len(paginas_a_procesar)

                for idx, (nombre_pag, img, num_pagina) in enumerate(paginas_a_procesar):
                    st.write(f"Analizando: **{nombre_pag}**...")
                    try:
                        # Procesar página con reintento y pausa integrada
                        res_pagina = procesar_pagina_parte_diario(img, nombre_archivo=nombre_pag)
                        
                        if res_pagina and hasattr(res_pagina, "registros") and res_pagina.registros:
                            # Se le asigna el número de página a cada registro
                            for reg in res_pagina.registros:
                                reg.pagina = num_pagina
                                todos_los_registros.append(reg)

                            st.success(f"✅ {nombre_pag}: {len(res_pagina.registros)} trabajador(es) extraídos.")
                        else:
                            st.warning(f"⚠️ {nombre_pag}: No se extrajeron registros.")
                        
                        # Pausa de cortesía entre páginas para evitar saturar la cuota gratuita (429)
                        if idx < total_paginas - 1:
                            time.sleep(6)

                    except Exception as e:
                        st.error(f"❌ Error en {nombre_pag}: {str(e)}")

                    barra_progreso.progress((idx + 1) / total_paginas)

            if todos_los_registros:
                st.session_state["registros_consolidados"] = todos_los_registros
                st.success(f"¡Procesamiento completo! Se consolidaron {len(todos_los_registros)} filas de asistencia.")

        if "registros_consolidados" in st.session_state and st.session_state["registros_consolidados"]:
            registros = st.session_state["registros_consolidados"]
            st.markdown("---")
            st.header(f"📊 Vista Previa de Asistencia ({len(registros)} Registros)")

            datos_df = [
                {
                    "PÁGINA": getattr(r, 'pagina', 1),
                    "FECHA": r.fecha, "TURNO": r.turno, "PROYECTO": r.proyecto,
                    "FRENTE": r.frente, "JEFE DE GRUPO": r.jefe_grupo,
                    "TRABAJADOR": r.nombres_apellidos, "DNI": r.dni,
                    "FASE": r.fase, "ACTIVIDAD": r.control_actividad,
                    "HH": r.hh, "ESTADO": r.estado
                }
                for r in registros
            ]
            st.dataframe(datos_df, use_container_width=True)

            excel_bytes = generar_excel_asistencia(registros)
            st.download_button(
                label=f"📥 Descargar Excel Consolidado ({len(registros)} filas)",
                data=excel_bytes,
                file_name="Control_Asistencia_Consolidado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

if __name__ == "__main__":
    main()
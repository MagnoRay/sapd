import sys
import os
import time
import io
import pymupdf
from PIL import Image
import streamlit as st

# Añade la raíz del proyecto al path de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.convertidor_pdf import convertir_pdf_a_imagenes, cargar_imagen_directa
from src.ia_vision_engine import procesar_pagina_parte_diario
from src.gestor_excel import generar_excel_asistencia

st.set_page_config(
    page_title="Control de Asistencia - Régimen C. Civil",
    page_icon="👷‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar archivos CSS y JS externos
def cargar_assets_interfaz():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    css_path = os.path.join(base_dir, 'assets', 'css', 'custom.css')
    js_path = os.path.join(base_dir, 'assets', 'js', 'custom.js')
    
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            
    if os.path.exists(js_path):
        with open(js_path, "r", encoding="utf-8") as f:
            st.components.v1.html(f"<script>{f.read()}</script>", height=0)

cargar_assets_interfaz()

def procesar_pdf_optimizado(archivo_bytes: bytes):
    doc = pymupdf.open(stream=archivo_bytes, filetype="pdf")
    imagenes_optimizadas = []
    
    for pagina in doc:
        pix = pagina.get_pixmap(dpi=150)
        img_pil = Image.open(io.BytesIO(pix.tobytes("jpeg")))
        
        ancho_max = 1200
        if img_pil.width > ancho_max:
            ratio = ancho_max / float(img_pil.width)
            alto_max = int(float(img_pil.height) * ratio)
            img_pil = img_pil.resize((ancho_max, alto_max), Image.Resampling.LANCZOS)
            
        imagenes_optimizadas.append(img_pil)
        
    return imagenes_optimizadas

def render_horas_hombre():
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
                        imagenes = procesar_pdf_optimizado(archivo_bytes)
                    else:
                        imagenes = [cargar_imagen_directa(archivo_bytes)]

                    for p_idx, img in enumerate(imagenes):
                        num_pagina = p_idx + 1
                        nombre_pag = f"{archivo.name} (Pág. {num_pagina})"
                        paginas_a_procesar.append((nombre_pag, img, num_pagina))

                except Exception as e:
                    st.error(f"Error cargando {archivo.name}: {str(e)}")

            if paginas_a_procesar:
                st.info(f"⚡ Procesando {len(paginas_a_procesar)} página(s) secuencialmente...")
                barra_progreso = st.progress(0)
                total_paginas = len(paginas_a_procesar)

                for idx, (nombre_pag, img, num_pagina) in enumerate(paginas_a_procesar):
                    st.write(f"Analizando: **{nombre_pag}**...")
                    try:
                        res_pagina = procesar_pagina_parte_diario(img, nombre_archivo=nombre_pag)
                        
                        if res_pagina and hasattr(res_pagina, "registros") and res_pagina.registros:
                            for reg in res_pagina.registros:
                                reg.pagina = num_pagina
                                todos_los_registros.append(reg)

                            st.success(f"✅ {nombre_pag}: {len(res_pagina.registros)} trabajador(es) extraídos.")
                        else:
                            st.warning(f"⚠️ {nombre_pag}: No se extrajeron registros.")
                        
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

def render_fixed_shell():
    # Navbar Superior AdminLTE4
    st.markdown("""
        <div class="adminlte-navbar">
            <div style="display: flex; align-items: center; gap: 16px;">
                <span style="font-size: 1.2rem; cursor: pointer; color: #495057;" onclick="window.parent.toggleAdminLTESidebar()">☰</span>
                <span style="color: #495057; font-size: 0.9rem; cursor: pointer;">📱 Live preview</span>
                <div style="position: relative; display: flex; align-items: center;">
                    <span style="position: absolute; left: 12px; color: #6c757d; font-size: 0.8rem;">🔍</span>
                    <input type="text" style="background: #f4f6f9; border: 1px solid #ced4da; padding: 6px 12px 6px 32px; border-radius: 20px; font-size: 0.85rem; width: 220px; outline: none;" placeholder="Documentation">
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <span style="cursor: pointer; color: #6c757d; font-size: 1rem;">💬</span>
                <span style="cursor: pointer; color: #6c757d; font-size: 1rem;">🔔</span>
                <span style="cursor: pointer; color: #6c757d; font-size: 1rem;">☀️</span>
                <span style="cursor: pointer; color: #6c757d; font-size: 1rem;">⛶</span>
                <div style="display: flex; align-items: center; gap: 8px; background: #f8f9fa; padding: 4px 12px; border-radius: 20px; border: 1px solid #e9ecef; cursor: pointer;">
                    <div style="background: #4b545c; color: #fff; border-radius: 50%; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: bold;">AP</div>
                    <span style="font-weight: 500; font-size: 0.85rem; color: #343a40;">Alexander Pierce</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Footer Fijo AdminLTE4
    st.markdown("""
        <div class="adminlte-footer">
            <div>
                <strong>Copyright &copy; 2026-2026 <a href="" target="_blank">Sapd</a>.</strong> Todos los derechos reservados.
            </div>
            <div>
                Todo lo que quieras
            </div>
        </div>
    """, unsafe_allow_html=True)

def main():
    if "nav_opcion" not in st.session_state:
        st.session_state["nav_opcion"] = "Horas Hombre"

    # Renderizar Navbar y Footer fijos una sola vez
    render_fixed_shell()

    # Sidebar Nativo estilizado como el menú charcoal de AdminLTE4
    with st.sidebar:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; padding: 5px 0 15px 0; border-bottom: 1px solid #4b545c; margin-bottom: 15px;">
            <div style="background: #ffffff; color: #212529; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.1rem;">A</div>
            <span style="font-size: 1.3rem; font-weight: 300; color: #ffffff; letter-spacing: 1px;">SAPD</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.text_input("Filter menu...", key="filter_menu_input", label_visibility="collapsed", placeholder="Filter menu...")
        
        opciones = [
            ("📊", "Dashboard", "Dashboard"),
            ("👷‍♂️", "Horas Hombre", "Horas Hombre"),
            ("🚜", "Horas Maquina", "Horas Maquina"),
            ("💰", "Gasto", "Gasto"),
            ("⚙️", "Configuración", "Configuración"),
            ("📖", "Documentacion", "Documentacion")
        ]

        for icono, label, val in opciones:
            es_activo = st.session_state["nav_opcion"] == val
            btn_label = f"{icono}  {label}"
            
            if st.button(btn_label, key=f"nav_{val}", use_container_width=True, type="primary" if es_activo else "secondary"):
                st.session_state["nav_opcion"] = val
                st.rerun()

    # Contenedor central con la clase wrapper para mantener el contenido centrado y desplazado del sidebar
    st.markdown('<div class="main-content-area"><div class="main-content-wrapper">', unsafe_allow_html=True)

    # Cabecera de la sección actual
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2 style="margin: 0; font-weight: 400; color: #343a40; font-size: 1.5rem;">{st.session_state["nav_opcion"]}</h2>
        <span style="color: #6c757d; font-size: 0.85rem;">Home / {st.session_state["nav_opcion"]}</span>
    </div>
    """, unsafe_allow_html=True)

    # Renderizar módulo activo
    if st.session_state["nav_opcion"] == "Horas Hombre":
        render_horas_hombre()
    elif st.session_state["nav_opcion"] == "Dashboard":
        st.info("📊 Panel de control principal (Dashboard).")
    else:
        st.info(f"Módulo **{st.session_state['nav_opcion']}** en desarrollo.")

    st.markdown('</div></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
import os
import streamlit as st

# Intenta obtener la clave desde los Secrets de Streamlit Cloud; si no está, la busca en el entorno (.env local)
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError, Exception):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Actualizado al modelo exigido por la API
MODEL_NAME = "gemini-3.8-flash"
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Actualizado al modelo exigido por la API
MODEL_NAME = "gemini-3.8-flash"
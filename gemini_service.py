"""A fresh, explicitly scoped Gemini client for each operation."""
import os
from google import genai
from google.genai.types import HttpOptions


def client():
    key = os.getenv('GEMINI_API_KEY','').strip()
    if not key:
        raise ValueError('Add GEMINI_API_KEY in Streamlit Settings → Secrets (hosted), or .env (local), then restart the app.')
    # Never let an unrelated Google Cloud environment select Vertex credentials.
    return genai.Client(api_key=key, vertexai=False, http_options=HttpOptions(timeout=90000))

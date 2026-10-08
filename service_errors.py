"""Useful diagnostics without printing credential-bearing request URLs."""
import os
import re
import requests
import httpx
from google.genai.errors import APIError


def redact_message(message):
    text = str(message or "")
    for name, value in os.environ.items():
        if value and len(value) >= 6 and any(part in name.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            text = text.replace(value, "[redacted]")
    text = re.sub(r"https?://[^\s<>]+", "[URL omitted]", text)
    text = re.sub(r"AIza[A-Za-z0-9_-]+", "[redacted]", text)
    text = re.sub(r"(?i)((?:api[_-]?key|access[_-]?token|authorization)\s*[:=]\s*)[^\s,;]+", r"\1[redacted]", text)
    return text[:1500]


def describe_error(error):
    service = "Study service"
    code = None
    message = ""
    if isinstance(error, APIError):
        service = "Gemini"
        code = error.code
        message = redact_message(error.message)
    elif isinstance(error, requests.exceptions.RequestException):
        service = "Transcript or dictionary service"
        if error.response is not None:
            code = error.response.status_code
        # requests errors may embed query strings carrying the SerpAPI key.
    lower = message.casefold()
    if code in (401, 403) or "api key not valid" in lower or "api_key_invalid" in lower:
        guidance = "The provider rejected the request's credentials or permissions. Check the matching API key in .env and restart Streamlit. For Gemini, confirm this is a Gemini API key and the project has API access."
    elif code == 404:
        guidance = "The requested model or resource was not found. If this is Gemini, check GEMINI_MODEL in .env against the model names available to your account, then restart Streamlit."
    elif code == 429:
        guidance = "The provider reports a rate or quota limit. Check the project's usage and limits. A short-term rate limit may clear after waiting; an exhausted quota needs a quota reset or account change."
    elif code == 400:
        guidance = "The provider rejected the request format. Check the diagnostic below: the chosen Gemini model may not support structured output or URL context. If passage context fails only with a commentary URL, try leaving that field blank."
    elif code is not None and code >= 500:
        guidance = "The provider is reporting a server error. Try again later."
    elif isinstance(error, (requests.exceptions.Timeout, httpx.TimeoutException, TimeoutError)):
        guidance = "The request timed out. Check your connection and try again."
    elif isinstance(error, (requests.exceptions.ConnectionError, httpx.ConnectError)):
        guidance = "Could not connect to the provider. Check your connection, VPN, proxy, or firewall."
    else:
        guidance = "The study failed. Share the diagnostic below so we can identify the cause."
    details = f"Service: {service}\nError type: {type(error).__name__}"
    if code is not None:
        details += f"\nHTTP status: {code}"
    if message:
        details += f"\nProvider message: {message}"
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    if re.fullmatch(r"[A-Za-z0-9./_-]{1,100}", model):
        details += f"\nConfigured Gemini model: {redact_message(model)}"
    embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    if re.fullmatch(r"[A-Za-z0-9./_-]{1,100}", embedding_model):
        details += f"\nConfigured embedding model: {redact_message(embedding_model)}"
    details += "\nGEMINI_API_KEY present: " + str(bool(os.getenv("GEMINI_API_KEY")))
    details += "\nSERPAPI_API_KEY present: " + str(bool(os.getenv("SERPAPI_API_KEY")))
    return guidance, details


def show_service_error(error, has_previous=False):
    import streamlit as st
    guidance, details = describe_error(error)
    st.error(guidance)
    if has_previous:
        st.caption("Your previous successful result is still available below.")
    with st.expander("Error details — safe to share", expanded=True):
        st.code(details, language="text")

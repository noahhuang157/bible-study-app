"""Reusable presentation elements. Only escaped text enters our HTML."""
from html import escape
from pathlib import Path
import streamlit as st

ICONS = {
    "memory": '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="m7 12 3 3 7-7M7 18h10"/>',
    "passage": '<path d="M12 5v15M12 5C9 3 5 3 2 4v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1Z"/>',
    "sermon": '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',
    "word": '<path d="M3 5h12M9 3v2M5 5c1 5 4 8 8 10M13 5c-1 5-4 8-8 10M14 21l4-10 4 10M15.5 17h5"/>',
}


def icon(kind, size=28):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[kind]}</svg>'


def apply_styles():
    css = (Path(__file__).parent / "assets" / "styles.css").read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def brand():
    st.markdown(f'<div class="brand"><span class="brand-mark">{icon("passage", 24)}</span><div><div class="brand-name">Scripture</div><div class="brand-subtitle">A study workspace</div></div></div>', unsafe_allow_html=True)


def page_intro(eyebrow, title, description):
    st.markdown(f'<div class="eyebrow">{escape(eyebrow)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.write(description)


def empty_state(kind, title, description):
    st.markdown(f'<div class="empty-state"><span class="empty-icon">{icon(kind, 34)}</span><h3>{escape(title)}</h3><p>{escape(description)}</p></div>', unsafe_allow_html=True)


def study_tip(text):
    st.markdown(f'<div class="study-tip">{escape(text)}</div>', unsafe_allow_html=True)

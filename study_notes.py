"""Personal notes are separate from AI output and keyed to their source study."""
import sqlite3
import streamlit as st
from storage import study_identity, get_study, update_notes
from accounts import current_user_id


def note_id(kind, result):
    return study_identity(kind,result)


def _sync_note(identity, widget_key):
    text = st.session_state[widget_key]
    st.session_state.setdefault("personal_notes", {})[identity] = text
    user_id = current_user_id()
    if not user_id:
        return
    try:
        record = get_study(user_id,identity)
        if record and record['notes'] != text:
            update_notes(user_id,identity,text)
    except (sqlite3.Error, OSError):
        st.warning('Could not save this note to disk. It remains in this session; download a copy before leaving.')


def show_personal_notes(kind, result):
    identity = note_id(kind, result)
    widget_key = "note_editor_" + identity
    saved = st.session_state.get("personal_notes", {}).get(identity, "")
    if current_user_id():
        try:
            record = get_study(current_user_id(),identity)
            if record:
                saved = record['notes']
        except (sqlite3.Error, OSError):
            st.warning('Could not load saved notes. Any current session note remains available.')
    st.subheader("My notes")
    st.caption("Write your observations, questions, and reflections. These are kept separately from study explanations.")
    st.text_area("Your study notes", value=saved, key=widget_key, height=240,
                 placeholder="What do I notice? What questions do I still have? How might I respond?",
                 on_change=_sync_note, args=(identity, widget_key))
    # Only the on_change callback writes to disk; rendering must not overwrite
    # a stored note if loading it temporarily failed.
    st.session_state.setdefault("personal_notes", {})[identity] = st.session_state[widget_key]
    text = st.session_state[widget_key]
    st.caption("Edits save to your local account when you finish editing the field. Download a copy any time.")
    if text.strip():
        title = result.get("label", result.get("query", "Study"))
        st.download_button("Download my notes ↓", f"# My notes · {title}\n\n{text}",
                           file_name="my-study-notes.md", mime="text/markdown", key="note_download_" + identity)
    return text

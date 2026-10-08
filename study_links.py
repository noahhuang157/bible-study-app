"""Navigation handoffs fill inputs without generating a study automatically."""
import streamlit as st


def open_passage(reference, source_url="", source_label="", translation=None):
    if translation:
        st.session_state["bible_translation"]=translation
        st.session_state["passage_translation_input"]=translation
    st.session_state["pending_passage"] = {
        "reference": reference, "source_url": source_url, "source_label": source_label,
    }
    st.switch_page("pages/passage_study.py")


def open_word(word, passage, translation=None):
    code=translation or st.session_state.get("bible_translation","WEB")
    st.session_state["word_translation_input"]=code
    st.session_state["pending_word"] = {"word": word, "passage": passage}
    st.switch_page("pages/word_study_page.py")


def consume_passage_link():
    previous = st.session_state.get("passage_result", {})
    st.session_state.setdefault("passage_input", previous.get("label", ""))
    st.session_state.setdefault("commentary_input", previous.get("requested_source", ""))
    pending = st.session_state.pop("pending_passage", None)
    if pending:
        st.session_state["passage_input"] = pending["reference"]
        # A commentary for the previous passage should not follow a new link.
        st.session_state["commentary_input"] = ""
        st.session_state["passage_origin"] = pending
    return st.session_state.get("passage_origin", {})


def consume_word_link():
    previous = st.session_state.get("word_result", {})
    st.session_state.setdefault("word_input", previous.get("query", ""))
    st.session_state.setdefault("word_passage_input", previous.get("passage", ""))
    pending = st.session_state.pop("pending_word", None)
    if pending:
        st.session_state["word_input"] = pending["word"]
        st.session_state["word_passage_input"] = pending["passage"]

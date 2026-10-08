import streamlit as st
from get_summary import get_sermon_study
from ui_common import generate_result, show_markdown_result
from design import page_intro, empty_state

page_intro("Listen, reflect, return", "Sermon Study", "Bring a sermon into your study. Follow its main points or work through a guided reflection.")
with st.form("sermon_form"):
    link = st.text_input("YouTube sermon URL", placeholder="https://www.youtube.com/watch?v=…")
    mode = st.radio("How would you like to study?", ["Structured Notes", "Inductive Study"], horizontal=True)
    st.caption("Follow the sermon’s outline, or explore Observation → Interpretation → Application.")
    submitted = st.form_submit_button("Prepare study notes →", type="primary")
if submitted:
    if not link.strip():
        st.warning("Enter a YouTube link first.")
    else:
        choice = "1" if mode == "Structured Notes" else "2"
        generate_result("sermon_result", f"Sermon · {mode}", lambda: get_sermon_study(link.strip(), choice))
if st.session_state.get("sermon_result"):
    show_markdown_result("sermon_result", "sermon-study")
else:
    empty_state("sermon", "Make room to revisit what you heard.", "Add a sermon with an available transcript. Your notes, reflection questions, and Scripture mentions will appear here.")
st.caption("Summaries reflect the transcript. Check the speaker’s teaching and extracted reference labels against Scripture.")

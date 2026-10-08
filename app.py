"""The shared frame: configure appearance, register pages, run one page."""
import streamlit as st
from design import apply_styles, brand
from accounts import require_account, account_sidebar
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

st.set_page_config(page_title="Scripture | Bible Study", page_icon="📖", layout="wide")
apply_styles()
with st.sidebar:
    brand()

require_account()
account_sidebar()

page = st.navigation({
    "Start": [st.Page("pages/home.py", title="Home", icon="🏠", default=True)],
    "Study": [
        st.Page("pages/passage_study.py", title="Passage Study", icon="📖"),
        st.Page("pages/word_study_page.py", title="Word Study", icon="🔤"),
        st.Page("pages/sermon_study.py", title="Sermon Study", icon="🎙️"),
        st.Page("pages/topic_study.py", title="Topic Study", icon="🌿"),
    ],
    "Practice": [st.Page("pages/memorize.py", title="Verse Memorization", icon="🧠")],
    "Your library": [
        st.Page("pages/my_studies.py", title="My Studies", icon="🗂️"),
        st.Page("pages/search_studies.py", title="Search by Meaning", icon="🔎"),
    ],
})
with st.sidebar:
    st.divider()
    st.caption("READ · REFLECT · RETURN")
    st.caption("Take your time with the text. Bring your questions here.")
    with st.expander("About this workspace"):
        st.write("Your studies, notes, and memory progress save to this app’s account storage. Export important work before a hosted trial resets.")
        st.caption("Check AI explanations against Scripture and trusted sources.")
page.run()

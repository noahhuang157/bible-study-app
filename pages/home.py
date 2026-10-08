import streamlit as st
from html import escape
from design import icon, study_tip
from accounts import current_user_id
from storage import list_studies
from memorization import memory_stats
from library_actions import reopen_study
import sqlite3

username = st.session_state['user']['username']
st.markdown(f'<div class="hero"><div class="eyebrow">Welcome back, {escape(username)}</div><h1>Study deeply.<br>Carry it with you.</h1><p>Read in context, explore the original words, and build a steady rhythm of remembering Scripture.</p><div class="hero-tag">A little attention. A daily return.</div></div>', unsafe_allow_html=True)
try:
    memory = memory_stats(current_user_id())
    if memory['total']:
        with st.container(border=True, key='daily-review'):
            left,right = st.columns([3,1])
            with left:
                st.markdown(f"**{memory['due']} verses or ranges ready for review**" if memory['due'] else '**Your reviews are up to date.**')
                st.caption(f"{memory['reviewed_today']} reviewed today · {memory['streak']}-day review streak")
            with right: st.page_link('pages/memorize.py',label='Practice now →')
except (sqlite3.Error,OSError):
    st.caption('Memory progress is temporarily unavailable.')
st.subheader("Where would you like to begin?")
cards = [
    ("passage", "Passage Study", "Read Bible text beside its context, word studies, and your personal notes.", "pages/passage_study.py"),
    ("sermon", "Sermon Study", "Turn a sermon into thoughtful notes, Scripture mentions, and questions to revisit.", "pages/sermon_study.py"),
    ("word", "Word Study", "See the original word, a clear meaning, and how it fits your passage.", "pages/word_study_page.py"),
]
for column, (kind, title, description, path) in zip(st.columns(3), cards):
    with column:
        with st.container(border=True, key=f"card-{kind}"):
            st.markdown(f'<div class="tool-card"><span class="icon-tile">{icon(kind)}</span><h3>{escape(title)}</h3><p>{escape(description)}</p></div>', unsafe_allow_html=True)
            st.page_link(path, label=f"Explore {title.lower()} →")

with st.container(border=True, key='memory-home'):
    st.markdown(f'<div class="memory-feature"><span class="icon-tile">{icon("memory")}</span><div><h3>Let the words stay with you.</h3><p>Flashcards, hidden-word practice, and typed recall. A review schedule that grows with you.</p></div></div>',unsafe_allow_html=True)
    st.page_link('pages/memorize.py',label='Open Verse Memorization →')
with st.expander('More ways to explore'):
    st.page_link("pages/my_studies.py", label="Open My Studies →")
    st.page_link("pages/topic_study.py", label="Explore a topic →")
    st.page_link("pages/search_studies.py", label="Search saved studies by meaning →")
try:
    recent = list_studies(current_user_id())[:3]
except (sqlite3.Error, OSError):
    recent = []
    st.warning("Your saved studies are temporarily unavailable.")
if recent:
    st.divider()
    st.subheader("Pick up where you left off")
    st.caption("Your most recently updated saved studies.")
    for record in recent:
        with st.container(border=True):
            st.write(record["title"])
            st.caption("Updated " + record["updated_at"][:10])
            if st.button("Continue study →", key="home_resume_" + record["id"]):
                reopen_study(record)
study_tip("Start with the passage itself. Notice what stands out, write down a question, then use these tools to explore it more deeply.")

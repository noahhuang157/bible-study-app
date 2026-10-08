"""Connect persistence to the UI without mixing it into provider services."""
import sqlite3
import streamlit as st
from accounts import current_user_id
from storage import save_study, get_study, study_identity, set_bookmark


def persist_result(kind, result):
    user_id = current_user_id()
    if not user_id:
        return False
    try:
        previous = get_study(user_id,study_identity(kind,result))
        if previous and kind == 'sermon_result':
            old = previous['payload']
            if old.get('transcript') and old.get('transcript') == result.get('transcript') and 'qa_history' not in result:
                result['qa_history'] = old.get('qa_history',[])
        save_study(user_id,kind,result)
        return True
    except (sqlite3.Error, OSError):
        st.warning('Your study is available below, but could not be saved. Check your data folder and download a copy before closing the app.')
        return False


def show_saved_actions(kind, result):
    user_id = current_user_id()
    if not user_id:
        return
    identity = study_identity(kind,result)
    try:
        record = get_study(user_id,identity)
        if not record:
            if not persist_result(kind,result):
                return
            record = get_study(user_id,identity)
        st.caption('Saved to My Studies on this computer.')
        bookmarked = record['bookmarked']
        if st.button('★ Bookmarked' if bookmarked else '☆ Bookmark this study', key='bookmark_' + identity):
            set_bookmark(user_id,identity,not bookmarked)
            st.rerun()
        st.page_link('pages/my_studies.py', label='View My Studies →')
    except (sqlite3.Error, OSError):
        st.warning('Could not access saved studies right now. Your current result remains available.')


def reopen_study(record):
    # The caller obtains this record through the current account's scoped query.
    kind = record['kind']
    st.session_state[kind] = record['payload']
    st.session_state.setdefault('personal_notes', {})[record['id']] = record['notes']
    st.session_state.pop('note_editor_' + record['id'], None)
    payload = record['payload']
    code=payload.get('reader',payload.get('passage_data',{})).get('translation_code','WEB')
    st.session_state['bible_translation']=code
    st.session_state['passage_translation_input']=code
    st.session_state['word_translation_input']=code
    if kind == 'passage_result':
        st.session_state['passage_input'] = payload['label']
        st.session_state['commentary_input'] = payload.get('requested_source','')
        st.session_state.pop('passage_origin',None)
        st.session_state.pop('pending_passage',None)
        target = 'pages/passage_study.py'
    elif kind == 'word_result':
        st.session_state['word_input'] = payload['query']
        st.session_state['word_passage_input'] = payload.get('passage','')
        st.session_state.pop('pending_word',None)
        st.session_state.pop('word_candidates',None)
        target = 'pages/word_study_page.py'
    elif kind == 'topic_result':
        st.session_state['topic_input']=payload['label']
        target='pages/topic_study.py'
    else:
        target = 'pages/sermon_study.py'
    st.switch_page(target)

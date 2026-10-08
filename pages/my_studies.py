import sqlite3
import streamlit as st
from accounts import current_user_id
from storage import list_studies, set_bookmark, export_backup
from library_actions import reopen_study
from design import page_intro, empty_state

page_intro('Keep what you discover', 'My Studies', 'Return to your passages, sermons, word studies, and personal reflections.')
st.page_link('pages/search_studies.py',label='Try search by meaning →')
query = st.text_input('Search studies and personal notes', placeholder='A passage, word, or phrase…')
kind_labels = {'All studies':'', 'Passages':'passage_result', 'Sermons':'sermon_result', 'Words':'word_result', 'Topics':'topic_result'}
kind = st.selectbox('Study type', list(kind_labels))
bookmarks = st.checkbox('Show bookmarks only')
user_id = current_user_id()
try:
    studies = list_studies(user_id,query,kind_labels[kind],bookmarks)
    backup = export_backup(user_id)
except (sqlite3.Error, OSError):
    st.error('Could not open your study library. Check that your data folder is writable.')
    st.stop()
with st.expander('Backup your studies'):
    st.write('Download all studies, notes, bookmark flags, and the memory deck for this account as JSON. The backup excludes account passwords and API keys.')
    st.download_button('Download account backup ↓', backup, file_name='scripture-studies-backup.json', mime='application/json')
    st.caption('For a complete local restore including your account, keep a copy of your data folder while the app is stopped. Instructions are in the README.')
if not studies:
    if query or bookmarks or kind != 'All studies':
        st.info('No studies match these filters. Try another search or clear the filters.')
    else:
        empty_state('passage','Your study library begins here.','Generate a passage, sermon, or word study. Successful results will be saved here automatically.')
else:
    st.caption(f"{len(studies)} studies · Most recently updated first")
    for record in studies:
        with st.container(border=True):
            st.subheader(record['title'])
            display_kind = {'passage_result':'Passage', 'sermon_result':'Sermon', 'word_result':'Word', 'topic_result':'Topic'}[record['kind']]
            st.caption(f"{display_kind} · Updated {record['updated_at'][:10]}" + (' · Bookmarked' if record['bookmarked'] else ''))
            if record['kind'] == 'word_result' and record['payload'].get('passage'):
                st.caption('Related passage: ' + record['payload']['passage'])
            if record['payload'].get('source_url'):
                st.caption('Sermon source: ' + record['payload']['source_url'])
            if record['notes']:
                st.write(record['notes'][:180] + ('…' if len(record['notes']) > 180 else ''))
            if st.button('Open study →', key='reopen_' + record['id']):
                reopen_study(record)
            if st.button('Remove bookmark' if record['bookmarked'] else 'Bookmark', key='library_bookmark_' + record['id']):
                try:
                    set_bookmark(user_id,record['id'],not record['bookmarked'])
                    st.rerun()
                except (sqlite3.Error, OSError):
                    st.warning('Could not update the bookmark. Please try again.')

import streamlit as st
from design import page_intro
from accounts import current_user_id
from advanced_study import semantic_search
from advanced_ui import tool_call
from storage import get_study
from library_actions import reopen_study

page_intro('Find the idea, not just the word','Search by Meaning','Find saved studies related to a question, theme, or idea—even when their titles use different words.')
with st.form('semantic_search'):
    query=st.text_input('What are you looking for?',placeholder='Trusting God when the future is uncertain',max_chars=500)
    labels={'All studies':'','Sermons':'sermon_result','Passages':'passage_result','Words':'word_result','Topics':'topic_result'}
    kind=st.selectbox('Search within',list(labels))
    bookmarked=st.checkbox('Bookmarked studies only')
    include_notes=st.checkbox('Include my personal notes',value=False)
    st.caption('Search sends your saved study text and transcripts to Gemini to build embeddings. Personal notes are included only if you select that option. Matching cached embeddings are reused; each query still makes an embedding call.')
    submit=st.form_submit_button('Search by meaning →',type='primary')
if submit:
    hits=tool_call(lambda:semantic_search(current_user_id(),query,labels[kind],bookmarked,include_notes))
    if hits is not None:
        st.session_state['semantic_hits']={'query':query,'hits':hits}
result=st.session_state.get('semantic_hits')
if result is not None:
    st.subheader('Results for '+result['query'])
    st.caption('Ranked by embedding similarity. Scores are not confidence percentages or proof of relevance.')
    if not result['hits']:
        st.info('No saved studies match the selected filters. Save a study or broaden the filters.')
    for index,hit in enumerate(result['hits']):
        record=get_study(current_user_id(),hit['id'])
        if record:
            with st.container(border=True):
                st.subheader(record['title'])
                st.caption(f"Similarity: {hit['score']:.3f}")
                st.write(hit['excerpt'])
                if st.button('Open saved study →',key=f'semantic_open_{index}'):
                    reopen_study(record)

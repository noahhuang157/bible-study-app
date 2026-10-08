"""Advanced tools run only on an explicit form submission or button click."""
import streamlit as st
from accounts import current_user_id
from storage import study_identity
from library_actions import persist_result
from study_links import open_passage
from service_errors import show_service_error
from advanced_study import ask_sermon, related_passages, contextual_word_guide


def tool_call(action):
    try:
        with st.spinner('Exploring your study…'):
            return action()
    except ValueError as error:
        st.warning(str(error))
    except Exception as error:
        show_service_error(error)
    return None


def render_suggestions(reading, origin, identity):
    st.caption('AI-generated suggested reading, not a verified cross-reference list. Read each passage in context.')
    for index, item in enumerate(reading.get('passages',[])):
        with st.container(border=True):
            st.write('**'+item['reference']+'**')
            st.write(item['reason'])
            st.caption('Context caution: '+item['caution'])
            if st.button('Study this passage →',key=f'related_{identity}_{index}'):
                open_passage(item['reference'],source_label=origin)
    if reading.get('limitations'):
        st.caption(reading['limitations'])


def related_panel(kind,result):
    identity=study_identity(kind,result)
    if kind == 'topic_result':
        render_suggestions({'passages':result.get('suggestions',[]),'limitations':result.get('limitations','')},result['label'],identity)
        return
    st.subheader('Read alongside this passage')
    st.write('Explore possible literary or thematic connections to '+result['label']+'.')
    if st.button('Suggest related passages →',key='suggest_'+identity):
        reading=tool_call(lambda:related_passages(result['label']))
        if reading is not None:
            result['related_reading']=reading
            persist_result(kind,result)
    if result.get('related_reading'):
        render_suggestions(result['related_reading'],result['label'],identity)


def sermon_questions(result):
    identity=study_identity('sermon_result',result)
    st.subheader('Ask this sermon')
    st.caption('Questions use selected transcript excerpts, not outside commentary. The embedding and answer calls run only when you submit.')
    if not result.get('transcript'):
        st.info('This older study has no saved transcript. Load it once to enable questions.')
        if st.button('Load original transcript',key='load_transcript_'+identity):
            from transcript import get_transcript
            from get_summary import get_video_id
            text=tool_call(lambda:get_transcript(get_video_id(result.get('source_url',''))))
            if text:
                result['transcript']=text
                persist_result('sermon_result',result)
                st.rerun()
        return
    with st.form('question_'+identity):
        question=st.text_input('Question about this sermon',placeholder='How did the speaker explain suffering?',max_chars=500)
        submitted=st.form_submit_button('Ask the transcript →',type='primary')
    if submitted:
        answer=tool_call(lambda:ask_sermon(current_user_id(),identity,question))
        if answer is not None:
            result.setdefault('qa_history',[]).append(answer)
            result['qa_history']=result['qa_history'][-20:]
            persist_result('sermon_result',result)
    for answer in reversed(result.get('qa_history',[])):
        with st.container(border=True):
            st.write('**'+answer['question']+'**')
            st.markdown(answer['answer'])
            for evidence in answer['evidence']:
                with st.expander('Transcript excerpt '+str(evidence['chunk'])):
                    st.write(evidence['quote'])
    st.caption('Matching excerpts checks wording, not whether every claim follows from them. Retrieval may miss relevant parts of a sermon. The latest 20 questions are kept.')
    with st.expander('Read the saved transcript'):
        st.text(result['transcript'])


def word_guidance(result):
    identity=study_identity('word_result',result)
    st.subheader('Explore the entry in context')
    st.caption('This guide uses the dictionary entry. It does not identify or grammatically tag the original-language word in your verse.')
    with st.form('word_guidance_'+identity):
        verse=st.text_area('Paste verse text (optional)',placeholder='Paste the verse you are reading from your Bible.',max_chars=5000)
        submit=st.form_submit_button('Generate word-study guidance →')
    if submit:
        guide=tool_call(lambda:contextual_word_guide(result,verse))
        if guide:
            result['word_guidance']=guide
            persist_result('word_result',result)
    if result.get('word_guidance'):
        st.markdown(result['word_guidance'])

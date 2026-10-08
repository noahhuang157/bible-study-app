import streamlit as st
from design import page_intro,empty_state
from advanced_study import topic_study
from ui_common import generate_result,show_markdown_result

page_intro('Follow a theme','Topic Study','Explore a biblical theme through suggested reading, context cautions, and reflection questions.')
st.session_state.setdefault('topic_input',st.session_state.get('topic_result',{}).get('label',''))
with st.form('topic_study'):
    topic=st.text_input('Topic to explore',placeholder='Hope, forgiveness, or hospitality',key='topic_input',max_chars=200)
    submit=st.form_submit_button('Explore this topic →',type='primary')
if submit:
    if topic.strip():
        generate_result('topic_result',topic.strip(),lambda:topic_study(topic.strip()))
    else:
        st.warning('Enter a topic first.')
if st.session_state.get('topic_result'):
    show_markdown_result('topic_result','topic-study')
else:
    empty_state('passage','Begin with a question or theme.','Your guide will suggest passages to read, explain possible connections, and leave space for your own reflections.')

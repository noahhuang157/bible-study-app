from html import escape
import re
import streamlit as st
from get_context import get_passage_context
from bible_reader import load_reading,reading_text
from translation_ui import translation_picker,show_attribution
from ui_common import download_text,show_sources
from design import page_intro,empty_state
from study_links import consume_passage_link,open_word
from study_notes import show_personal_notes
from library_actions import persist_result,show_saved_actions
from accounts import current_user_id
from storage import get_study,study_identity
from advanced_ui import related_panel
from service_errors import show_service_error


def read_request(reference,source_url='',generate=False,translation=None):
    """Load the selected reference first; never attach another passage's context."""
    translation=translation or st.session_state.get('bible_translation','WEB')
    try:
        with st.spinner('Opening the passage…'):
            reader=load_reading(reference,translation)
        baseline={'label':reference.strip(),'text':'','reader':reader}
        identity=study_identity('passage_result',baseline)
        current=st.session_state.get('passage_result',{})
        if current and study_identity('passage_result',current)==identity:
            baseline={**current,'reader':reader}
        else:
            record=get_study(current_user_id(),identity)
            if record:baseline={**record['payload'],'reader':reader}
        # Backgrounds are specific to the translation used to generate them;
        # personal notes retain the existing passage identity across versions.
        contexts=dict(baseline.get('context_by_translation',{}))
        if baseline.get('text'):
            contexts.setdefault(baseline.get('context_translation','WEB'),{k:baseline[k] for k in ['text','sources','requested_source'] if k in baseline})
        baseline.update({'text':'','sources':[],'requested_source':'','context_by_translation':contexts,'context_translation':translation})
        baseline.update(contexts.get(translation,{}))
        st.session_state['bible_translation']=translation
        st.session_state['passage_result']=baseline
        if generate:
            try:
                with st.spinner('Exploring the passage in context…'):
                    payload=get_passage_context(reference.strip(),source_url.strip(),reader['translation']+'\n'+reading_text(reader,whole_chapter=True))
                if not payload.get('text','').strip():raise ValueError('No context was returned. Please try again.')
                baseline={**baseline,**payload,'label':reference.strip(),'reader':reader}
                contexts[translation]={k:payload[k] for k in ['text','sources','requested_source'] if k in payload}
                baseline['context_by_translation']=contexts
                st.session_state['passage_result']=baseline
                st.success('Your passage and context are ready below.')
            except ValueError as error:st.warning(str(error))
            except Exception as error:show_service_error(error,has_previous=bool(baseline.get('text')))
        persist_result('passage_result',baseline)
    except ValueError as error:st.warning(str(error))
    except Exception as error:show_service_error(error,has_previous=bool(st.session_state.get('passage_result')))


def navigate_chapter(reference):
    # Button callbacks run before widget creation, making the input update safe.
    st.session_state['passage_input']=reference
    st.session_state['commentary_input']=''
    st.session_state['reader_request']=reference
    st.session_state.pop('passage_origin',None)


def show_verses(rows,selected=None):
    selected=selected or set()
    markup=''.join(f'<div class="bible-verse{" bible-verse-selected" if row["verse"] in selected else ""}"><span class="bible-verse-number">{str(row["verse"])+("–"+str(row["verse_end"]) if row.get("verse_end",row["verse"])!=row["verse"] else "")}</span><span>{escape(row["text"])}</span></div>' for row in rows)
    st.markdown('<div class="bible-reading-text">'+markup+'</div>',unsafe_allow_html=True)


page_intro('Read · Reflect · Explore','Passage Study','Read the passage, follow its surrounding context, and keep your study beside the text.')
linked=bool(st.session_state.get('pending_passage'))
origin=consume_passage_link()
if linked:
    read_request(origin['reference'])
if st.session_state.get('reader_request'):
    read_request(st.session_state.pop('reader_request'))
if origin and st.session_state.get('passage_input')==origin.get('reference'):
    st.caption(f"Opened from {origin.get('source_label') or 'your study'}. Bible text opens in your chosen version; context generation runs only when requested.")
    if origin.get('source_url'):st.link_button('Return to original sermon ↗',origin['source_url'])
with st.form('passage_form'):
    passage=st.text_input('Which passage are you studying?',placeholder='John 15:1–17',key='passage_input')
    source_url=st.text_input('Commentary URL (optional)',placeholder='https://enduringword.com/bible-commentary/john-15/',key='commentary_input')
    translation=translation_picker('passage_translation_input')
    st.caption('Read a chapter or verse range within one chapter. WEB reading works offline; other versions require provider access. Explore context uses your Gemini key.')
    read=st.form_submit_button('Read passage →',type='primary')
    explore=st.form_submit_button('Explore context →')
if read or explore:
    if not passage.strip():st.warning('Enter a passage first, such as John 15:1–17.')
    else:read_request(passage.strip(),source_url,generate=explore,translation=translation)

result=st.session_state.get('passage_result')
if result:
    identity=study_identity('passage_result',result)
    st.subheader(result['label'])
    show_saved_actions('passage_result',result)
    reader=result.get('reader')
    if not reader or reader.get('requires_fetch'):
        code=(reader or {}).get('translation_code','WEB')
        attempt_key='reader_fetch_failed_'+identity+'_'+code
        if st.session_state.get(attempt_key):
            reader=None
            if st.button('Retry loading Bible text',key='retry_'+identity):
                st.session_state.pop(attempt_key,None);st.rerun()
        else:
            try:
                reader=load_reading(result['label'],code);result['reader']=reader
            except ValueError as error:
                reader=None;st.session_state[attempt_key]=True;st.warning(str(error))
                st.info('Your saved explanation and notes remain available. Retry loading text or choose a version you can access.')
            except Exception as error:
                reader=None;st.session_state[attempt_key]=True;show_service_error(error)
    left,right=st.columns([1.1,1],gap='large')
    with left:
        st.subheader('Read the text')
        if reader:
            st.caption(reader['translation']+' · verse numbers shown beside the text')
            show_attribution(reader)
            prev,next_=st.columns(2)
            prev.button('← Previous chapter',disabled=not reader['previous_chapter'],key='reader_prev',on_click=navigate_chapter,args=(reader['previous_chapter'],))
            next_.button('Next chapter →',disabled=not reader['next_chapter'],key='reader_next',on_click=navigate_chapter,args=(reader['next_chapter'],))
            with st.container(border=True):show_verses(reader['selected'])
            if st.button('Practice memorizing this passage →',key='reader_memorize'):
                st.session_state['memory_reference']=result['label']
                st.session_state['memory_translation']=reader.get('translation_code','WEB')
                st.switch_page('pages/memorize.py')
            if not reader['is_whole_chapter']:
                with st.expander('Read surrounding context · '+reader['chapter_reference']):
                    st.caption('Your selected verses are highlighted within the full chapter.')
                    show_verses(reader['chapter'],{r['verse'] for r in reader['selected']})
                st.button('Read the full chapter →',key='reader_full',on_click=navigate_chapter,args=(reader['chapter_reference'],))
            st.caption('WEB text is displayed separately from original-language tags. English words are not yet individually linked to Greek or Hebrew.')
        else:st.info('Bible text is unavailable for this saved reference.')
    with right:
        st.subheader('Study beside the passage')
        context,words,related,notes,sources=st.tabs(['Context','Word study','Related reading','My notes','Sources & download'])
        with context:
            if result.get('text'):
                st.caption('AI-generated background · '+result.get('context_translation','WEB')+'. Check its claims against the passage and sources.')
                st.markdown(result['text'])
            else:
                st.info('Start with the text and record what you notice. Select Explore context above when you want background for this passage.')
        with words:
            st.subheader('Explore a word')
            st.caption('Choose a word or Strong’s number. Word Study will check candidate original words against the selected passage.')
            with st.form('reader_word_'+identity):
                word=st.text_input('Word to explore',placeholder='love, agape, or G26')
                options=[result['label']]+([r['reference'] for r in reader['selected']] if reader and len(reader['selected'])>1 else [])
                selected=st.selectbox('Word study passage',options)
                go=st.form_submit_button('Open Word Study →')
            if go:
                if word.strip():open_word(word.strip(),selected)
                else:st.warning('Enter a word to explore first.')
        with related:related_panel('passage_result',result)
        with notes:personal_notes=show_personal_notes('passage_result',result)
        with sources:
            if reader:st.caption('Displayed version: '+reader['translation'])
            show_sources(result)
            filename=re.sub(r'[^a-zA-Z0-9_-]+','-',result['label']).strip('-')[:80]
            st.download_button('Download passage & study ↓',download_text(result,personal_notes),file_name=(filename or 'passage-study')+'.md',mime='text/markdown')
            if reader:st.download_button('Download selected Bible text ↓',reader['translation']+'\n'+reader.get('copyright','')+'\n\n'+reading_text(reader),file_name=(filename or 'bible-text')+'-'+reader.get('translation_code','WEB')+'.txt',mime='text/plain')
else:empty_state('passage','Start with the passage itself.','Enter a reference and select Read passage. Add background, word studies, and your notes as you read.')

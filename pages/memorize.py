"""Verse memorization: no AI calls, no persistent licensed Bible text."""
import sqlite3
import os
import uuid
from html import escape
import streamlit as st
from accounts import current_user_id
from bible_reader import load_reading
from translation_ui import translation_picker, show_attribution
from design import page_intro, empty_state
from memorization import (add_card,list_cards,remove_card,review_card,memory_stats,
                          export_deck,today,check_recall,hidden_words)

page_intro('Remember · Practice · Return','Verse Memorization',
           'Keep Scripture close. Practice a little at a time and return when a verse is due.')
user_id = current_user_id()
try:
    cards = list_cards(user_id)
    stats = memory_stats(user_id)
except (sqlite3.Error,OSError):
    st.error('Could not open your memory deck. Check that your data folder is writable.')
    st.stop()
with st.container(key='memory-stats'):
    cols = st.columns(4)
    for col,(label,value) in zip(cols,[('Verses & ranges',stats['total']),('Due for review',stats['due']),('Reviewed today',stats['reviewed_today']),('Review streak',f"{stats['streak']} days")]):
        col.metric(label,value)
practice, deck, add = st.tabs(['Practice','My deck','Add a verse'])

with add:
    st.subheader('Choose a verse to remember')
    with st.form('memory_add'):
        reference = st.text_input('Passage to memorize',placeholder='John 15:5 or Psalm 23:1–3',key='memory_reference')
        translation = translation_picker('memory_translation')
        collection = st.text_input('Collection (optional)',placeholder='Peace, promises, this week…',max_chars=60)
        st.caption('One verse or up to five verses in the same chapter. No AI key is needed.')
        submitted = st.form_submit_button('Add to my deck →',type='primary')
    if submitted:
        try:
            if not reference.strip(): raise ValueError('Enter a verse reference first.')
            with st.spinner('Loading your verse…'):
                reading = load_reading(reference.strip(),translation)
            identity, created = add_card(user_id,reading,collection)
            st.session_state['memory_reading'] = {'id':identity,'reading':reading}
            st.session_state['memory_next'] = identity
            st.session_state['memory_notice'] = 'Verse added. Open Practice to begin.' if created else 'This verse is already in your deck. Its collection was updated; review progress was kept.'
            st.rerun()
        except ValueError as error: st.warning(str(error))
        except (sqlite3.Error,OSError): st.error('Could not save the verse. Please try again.')
        except Exception: st.error('Could not load this verse. Check your provider access and try again.')

if st.session_state.get('memory_notice'):
    st.success(st.session_state.pop('memory_notice'))

with deck:
    st.subheader('Your memory deck')
    if cards:
        collection_filter = st.selectbox('Collection',['All collections']+sorted({c['collection'] for c in cards if c['collection']}))
        for card in cards:
            if collection_filter!='All collections' and card['collection']!=collection_filter: continue
            with st.container(border=True):
                st.markdown(f"**{card['reference']} · {card['translation']}**")
                due = 'Due today' if card['due_date']<=today().isoformat() else 'Next review '+card['due_date']
                st.caption(f"{card['collection'] or 'My verses'} · {due} · {card['reviews']} reviews")
                with st.expander('Manage this verse'):
                    confirm = st.checkbox('Remove this verse and its review history',key='memory_confirm_'+card['id'])
                    if st.button('Remove verse',key='memory_delete_'+card['id'],disabled=not confirm):
                        remove_card(user_id,card['id']); st.session_state.pop('memory_attempt',None); st.rerun()
        st.download_button('Download memory deck ↓',export_deck(user_id),file_name='scripture-memory-deck.json',mime='application/json')
        st.caption('The export contains verse references, collections, and schedules. Bible text and passwords are excluded.')
    else:
        empty_state('memory','A little practice begins here.','Open Add a verse to start your first collection.')

with practice:
    if not cards:
        st.info('Add a verse, then return here to practice.')
    else:
        scope = st.radio('Review queue',['Due for review','All verses'],horizontal=True,key='memory_scope')
        if scope=='All verses': st.caption('Extra practice is welcome. Rating an early review also updates its schedule.')
        pool = [c for c in cards if scope=='All verses' or c['due_date']<=today().isoformat()]
        if not pool:
            st.success('You’re caught up. Return on your next review date or choose All verses for extra practice.')
        else:
            by_id = {c['id']:c for c in pool}
            next_card = st.session_state.pop('memory_next',None)
            if next_card in by_id: st.session_state['memory_card'] = next_card
            if st.session_state.get('memory_card') not in by_id:
                st.session_state['memory_card'] = pool[0]['id']
            identity = st.selectbox('Verse to practice',list(by_id),format_func=lambda i:f"{by_id[i]['reference']} · {by_id[i]['translation']}",key='memory_card')
            card = by_id[identity]
            mode = st.radio('Practice mode',['Flashcard','Hide words','Typed recall'],horizontal=True,key='memory_mode')
            marker = identity+'|'+mode
            attempt = st.session_state.get('memory_attempt')
            if not attempt or attempt['marker']!=marker:
                for old_key in list(st.session_state):
                    if old_key.startswith('memory_answer_'): st.session_state.pop(old_key,None)
                attempt = {'marker':marker,'token':uuid.uuid4().hex,'revealed':False,'feedback':None}
                st.session_state['memory_attempt'] = attempt
            cache = st.session_state.get('memory_reading',{})
            failed_key = 'memory_load_failed_'+identity
            if cache.get('id')!=identity and not st.session_state.get(failed_key):
                try:
                    with st.spinner('Opening your verse…'):
                        reading = load_reading(card['reference'],card['translation'])
                    cache = {'id':identity,'reading':reading}
                    st.session_state['memory_reading'] = cache
                except Exception as error:
                    st.session_state[failed_key] = str(error) if isinstance(error,ValueError) else 'The Bible text provider is unavailable.'
            if cache.get('id')!=identity:
                st.warning(st.session_state.get(failed_key,'Could not load this verse.'))
                st.caption('Your progress is saved. Licensed versions need provider access when reopened.')
                if st.button('Retry loading verse'):
                    st.session_state.pop(failed_key,None); st.rerun()
            else:
                reading = cache['reading']
                text = ' '.join(r['text'] for r in reading['selected'])
                st.markdown(f'<div class="memory-heading">{escape(card["reference"])} <span>{escape(card["translation"])}</span></div>',unsafe_allow_html=True)
                show_attribution(reading)
                if mode=='Flashcard':
                    st.caption('Say or write the verse from memory, then reveal the text.')
                    body = text if attempt['revealed'] else 'Take a breath. Recall the words.'
                elif mode=='Hide words':
                    level = st.select_slider('How much to hide',['Some words','Most words','All words'],value='Some words')
                    body = text if attempt['revealed'] else hidden_words(text,level)
                    st.caption('Use the visible words as cues. Increase the difficulty when you are ready.')
                else:
                    body = text if attempt['revealed'] else 'Write the verse in your own time.'
                    with st.form('recall_'+attempt['token']):
                        answer = st.text_area('Your recall attempt',height=140,max_chars=10000,key='memory_answer_'+attempt['token'])
                        checked = st.form_submit_button('Check my recall →',type='primary')
                    if checked:
                        try:
                            attempt['feedback'] = check_recall(answer,text)
                            attempt['revealed'] = True
                            st.rerun()
                        except ValueError as error: st.warning(str(error))
                st.markdown('<div class="memory-card">'+escape(body)+'</div>',unsafe_allow_html=True)
                if attempt['feedback']:
                    feedback = attempt['feedback']
                    if feedback['exact']: st.success('The wording matches. Capitalization and punctuation are ignored.')
                    else:
                        st.info(f"Wording match: {feedback['score']}%. Compare your attempt with the verse above. Extra and missing words affect the match.")
                        st.caption('This is a practice aid, not a measure of understanding. You choose the review rating.')
                if not attempt['revealed']:
                    if st.button('Reveal verse',key='reveal_'+attempt['token']):
                        attempt['revealed']=True; st.rerun()
                else:
                    st.write('How did recall feel?')
                    st.caption('Again: tomorrow · Hard: shorter interval · Good: normal interval · Easy: longer interval')
                    cols = st.columns(4)
                    for col,rating in zip(cols,['Again','Hard','Good','Easy']):
                        if col.button(rating,key='rate_'+rating+'_'+attempt['token'],width='stretch'):
                            try:
                                review_card(user_id,identity,rating,attempt['token'])
                                updated = next(c for c in list_cards(user_id) if c['id']==identity)
                                st.session_state['memory_notice'] = f"Review saved. {card['reference']} is next due {updated['due_date']}."
                                st.session_state.pop('memory_attempt',None)
                                remaining = [c for c in pool if c['id']!=identity]
                                if remaining: st.session_state['memory_next'] = remaining[0]['id']
                                st.rerun()
                            except (ValueError,sqlite3.Error,OSError): st.warning('Could not save the review. Please try again.')
                if st.button('Start a fresh attempt',key='fresh_'+identity):
                    st.session_state.pop('memory_attempt',None); st.rerun()
        st.caption('Review dates use '+os.getenv('SCRIPTURE_TIMEZONE','America/Los_Angeles')+'. Progress saves to this app’s account storage.')

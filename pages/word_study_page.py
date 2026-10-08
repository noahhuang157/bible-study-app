from html import escape
import math
import os
import streamlit as st
from word_study import (clean, search_entries, passage_material, occurrences, greek_morphology)
from word_explanation import generate_word_explanation,generate_word_meaning
from translation_ui import translation_picker,show_attribution
from design import page_intro, empty_state
from study_links import consume_word_link, open_passage
from study_notes import show_personal_notes
from service_errors import show_service_error
from library_actions import persist_result, show_saved_actions
from storage import study_identity


def save_selection(pending,entry):
    material=passage_material(pending['passage'],entry,pending.get('translation','WEB')) if pending['passage'] else None
    result={'query':pending['query'],'entry':entry,'passage':pending['passage'],'word_version':2,'label':f"{pending['query']} · {entry['topic']} · {entry['transliteration']}"}
    if material:result['passage_data']=material
    st.session_state['bible_translation']=pending.get('translation','WEB')
    if pending.get('clear_meaning',True) and os.getenv('GEMINI_API_KEY'):
        try:
            with st.spinner('Explaining the meaning clearly…'):result['meaning_summary']=generate_word_meaning(result)
        except ValueError as error:st.warning('The word was found, but its plain-language explanation could not be generated: '+str(error))
        except Exception as error:show_service_error(error)
    st.session_state['word_result']=result
    persist_result('word_result',result)
    st.session_state.pop('word_candidates',None)


def candidate_label(entry):
    match=f" · {entry['passage_matches']} in your passage" if entry.get('passage_matches') else ''
    return f"{entry['lexeme']} · {entry['transliteration']} · {entry['topic']} [{entry['lemma_id']}] · {entry['short_definition']}"+match


def verse_rows(rows):
    for row in rows:
        st.markdown(f"**{row['reference']}** — {row['text']}")


page_intro('Explore the language','Word Study','See the original word, understand its use in a passage, and compare verified occurrences.')
consume_word_link()
with st.form('word_form'):
    word=st.text_input('Word or Strong’s number',placeholder='love, agape, or G26',key='word_input')
    passage=st.text_input('Passage to study (optional)',placeholder='John 15:9–17',key='word_passage_input')
    translation=translation_picker('word_translation_input')
    clear_meaning=st.checkbox('Include a clear meaning explanation',value=True,help='Uses Gemini once when you select a word. Without a Gemini key, the sourced lexical information still appears.')
    st.caption('Use a chapter or a verse range within one chapter. Add a passage for verified word forms and an in-depth explanation.')
    submitted=st.form_submit_button('Find word →',type='primary')
if submitted:
    if not word.strip():st.warning('Enter a word first.')
    else:
        st.session_state.pop('word_candidates',None)
        try:
            with st.spinner('Finding words in the local lexicon…'):
                entries,total=search_entries(word.strip(),passage.strip())
            if entries:
                pending={'query':word.strip(),'passage':passage.strip(),'entries':entries,'total':total,'translation':translation,'clear_meaning':clear_meaning}
                if len(entries)==1:save_selection(pending,entries[0])
                else:st.session_state['word_candidates']=pending
            else:
                st.session_state.pop('word_candidates',None)
                st.warning('No entry found. Try a Strong’s number, another spelling, or a shorter English word. Your previous study remains below.')
        except ValueError as error:st.warning(str(error))
        except Exception as error:show_service_error(error,has_previous=bool(st.session_state.get('word_result')))

pending=st.session_state.get('word_candidates')
if pending:
    st.subheader('Choose the original word')
    st.caption(f"{pending['total']} lexical matches. Words found in your passage appear first. Greek and Hebrew equivalents can have different meanings.")
    if pending['total']>len(pending['entries']):st.info('Showing the first 150 matches. Narrow your search or use a Strong’s number.')
    with st.form('choose_word_'+pending['query']+'_'+pending['passage']):
        available=pending['entries']
        choice=st.selectbox('Original word',range(len(available)),index=None,format_func=lambda i:candidate_label(available[i]),placeholder='Choose a word to study')
        chosen=st.form_submit_button('Study selected word →',type='primary')
    if chosen:
        if choice is None:st.warning('Choose an original word first.')
        else:
            try:save_selection(pending,available[choice]);st.rerun()
            except Exception as error:show_service_error(error,has_previous=bool(st.session_state.get('word_result')))

result=st.session_state.get('word_result')
if result:
    entry=result['entry'];identity=study_identity('word_result',result)
    material=result.get('passage_data')
    if material and material.get('requires_fetch'):
        attempt_key='word_fetch_failed_'+identity+'_'+material.get('translation_code','WEB')
        if st.session_state.get(attempt_key):
            if st.button('Retry loading passage text',key='retry_'+identity):
                st.session_state.pop(attempt_key,None);st.rerun()
        else:
            try:result['passage_data']=passage_material(result['passage'],entry,material.get('translation_code','WEB'))
            except ValueError as error:st.session_state[attempt_key]=True;st.warning(str(error))
            except Exception as error:st.session_state[attempt_key]=True;show_service_error(error)
    st.markdown('<div class="result-meta">Your word study</div>',unsafe_allow_html=True)
    lexeme=entry.get('lexeme') or entry.get('topic') or result['query']
    language='Greek' if entry.get('topic','').startswith('G') else 'Hebrew / Aramaic'
    display_meaning=result.get('meaning_summary',{}).get('plain_meaning') or clean(entry.get('short_definition')) or 'Dictionary word'
    direction='rtl' if entry.get('topic','').startswith('H') else 'ltr'
    st.markdown(f'<div class="word-overview"><div class="word-script" dir="{direction}">{escape(lexeme)}</div><div class="word-transliteration">{escape(entry.get("transliteration") or "")}</div><div class="word-gloss">{escape(display_meaning)}</div></div>',unsafe_allow_html=True)
    st.caption(f"{language} · Strong’s {entry.get('topic','Not provided')} · {entry.get('lemma_id','Legacy dictionary entry')} · {entry.get('source','Bolls BDBT dictionary')}")
    if entry.get('transliteration_scope')=='attested form':st.caption('Transliteration is from an attested word form; this corpus ID has no separate brief-lexicon entry.')
    show_saved_actions('word_result',result)
    overview,context,uses,personal,details=st.tabs(['Word overview','Meaning in context','Other occurrences','My notes','Sources & download'])
    with overview:
        st.subheader('Start with the meaning')
        summary=result.get('meaning_summary')
        if summary:
            st.markdown('**Plain-language meaning**')
            st.write(summary['plain_meaning'])
            if summary.get('contextual_meaning'):
                st.markdown('**Meaning in '+result.get('passage','this passage')+'**')
                st.write(summary['contextual_meaning'])
                st.caption('Passage version: '+summary.get('translation','WEB'))
                st.write(summary['why_this_meaning'])
            if summary.get('other_senses'):
                with st.expander('Other possible senses—not all apply here'):
                    for sense in summary['other_senses']:st.write('• '+sense)
            st.caption(summary['caution'])
            st.caption('Evidence: '+', '.join(summary['references']))
        elif result.get('word_explanation',{}).get('sections',{}).get('meaning'):
            st.markdown('**Meaning in this passage**')
            st.write(result['word_explanation']['sections']['meaning']['text'])
        else:
            definition_preview=clean(entry.get('definition'))
            if definition_preview:
                st.markdown('**From the lexical source**')
                st.write(definition_preview[:1000]+('…' if len(definition_preview)>1000 else ''))
            else:st.info('Only a brief glossary is available for this entry. Add a passage to establish its specific use.')
        if st.button('Explain this word clearly →',key='clear_meaning_'+identity):
            try:
                with st.spinner('Explaining the word and its context…'):result['meaning_summary']=generate_word_meaning(result)
                persist_result('word_result',result);st.rerun()
            except ValueError as error:st.warning(str(error))
            except Exception as error:show_service_error(error)
        with st.expander('Short dictionary gloss'):st.write(clean(entry.get('short_definition')))
        st.caption('This is a dictionary gloss. The sentence and surrounding argument determine the sense in a specific passage.')
        if entry.get('grammar'):st.write('Dictionary grammar: '+entry['grammar'])
        definition=clean(entry.get('definition'))
        if definition:
            with st.expander('Read the full lexical entry'):
                st.markdown(f'<div class="dictionary-definition">{escape(definition)}</div>',unsafe_allow_html=True)
        else:
            st.info('This entry provides a concise source gloss and word metadata. A full lexical definition is not bundled for this entry.')
        if entry.get('topic'):
            topic=entry['topic'].lower()
            st.link_button('Compare this entry on Blue Letter Bible ↗',f'https://www.blueletterbible.org/lexicon/{topic}/kjv/tr/0-1/')
    with context:
        material=result.get('passage_data')
        if not result.get('passage'):
            st.info('Enter a passage above to study this word in context.')
        elif not material:
            st.info('This saved study predates verified passage data. Load its passage to check the selected Strong’s number.')
            if st.button('Load passage and verify word',key='load_passage_'+identity):
                try:
                    result['passage_data']=passage_material(result['passage'],entry,st.session_state.get('bible_translation','WEB'))
                    persist_result('word_result',result);st.rerun()
                except ValueError as error:st.warning(str(error))
                except Exception as error:show_service_error(error)
        if material and material.get('selected'):
            st.subheader(result['passage'])
            st.caption(material['translation']+' · original-word tags: '+material['edition'])
            show_attribution(material)
            verse_rows(material['selected'])
            if st.button('Open passage study →',key='passage_'+identity):open_passage(result['passage'],source_label='Word Study',translation=material.get('translation_code','WEB'))
            if material['verified']:
                st.success(f"Verified {len(material['matches'])} occurrence(s) in this passage using {material['matching_scope']}.")
                st.subheader('The word as it appears here')
                for match in material['matches']:
                    with st.container(border=True):
                        st.markdown(f"### {match['surface']}")
                        st.write(f"{match['reference']} · {match['transliteration']}")
                        st.write('Source translation gloss: '+match['gloss'])
                        st.caption('Source grammar: '+match['morphology'])
                        if language=='Greek':st.write(greek_morphology(match['morphology']))
                        else:st.caption('Hebrew forms may include prefixes or suffixes; the match can concern one component of the displayed word.')
                st.caption('The original word is verified in the source edition. English words are not individually aligned to these tags.')
                with st.expander('Read the surrounding chapter ('+material.get('translation_code','WEB')+')'):verse_rows(material['chapter'])
                st.subheader('Understand this use in depth')
                st.caption('AI explanation grounded in the lexical entry, tagged forms, surrounding chapter, and retrieved occurrences. Historical inferences and interpretations still require review.')
                focus=st.text_area('What would you like clarified? (optional)',placeholder='For example: How does this word connect to the command in the next verse?',max_chars=2000,key='word_focus_'+identity)
                if st.button('Explain this passage in depth →',type='primary',key='explain_'+identity):
                    try:
                        with st.spinner('Reading the word in its surrounding argument…'):
                            explanation=generate_word_explanation({**result,'reader_question':focus})
                        result['word_explanation']=explanation
                        result['word_guidance']=explanation['markdown']
                        persist_result('word_result',result)
                    except ValueError as error:st.warning(str(error))
                    except Exception as error:show_service_error(error,has_previous=bool(result.get('word_guidance')))
            else:
                st.warning('This selected original word was not found in the passage in this edition. Choose a matching word before requesting an explanation.')
                st.caption('An English translation may use another original word, or editions may differ. Try a shorter passage or another lexical match.')
        if result.get('word_explanation'):
            st.markdown(result['word_explanation']['markdown'])
        elif result.get('word_guidance'):
            with st.expander('Previously saved guidance (before this upgrade)'):st.markdown(result['word_guidance'])
    with uses:
        st.subheader('Where this word occurs')
        try:
            all_uses=occurrences(entry,limit=0)
            st.caption('Verified from STEP original-word tags; previews use WEB. Counts use the selected extended lexical ID and edition. These are word occurrences; related themes may use different words.')
            c1,c2,c3=st.columns(3)
            c1.metric('Word occurrences',all_uses['tokens']);c2.metric('Verses',all_uses['verse_count']);c3.metric('Books',len(all_uses['books']))
            options=[None]+[r['book'] for r in all_uses['books']]
            names={r['book']:r['name'] for r in all_uses['books']}
            book=st.selectbox('Filter by book',options,format_func=lambda b:names[b] if b else 'All books',key='occurrence_book_'+identity)
            count=next((r['verses'] for r in all_uses['books'] if r['book']==book),all_uses['verse_count'])
            pages=max(1,math.ceil(count/15))
            page=st.number_input('Results page',min_value=1,max_value=pages,value=1,step=1,key='occurrence_page_'+identity+'_'+str(book))
            rows=occurrences(entry,book=book,offset=(page-1)*15,limit=15)
            st.caption(f"Page {page} of {pages} · {count} verses")
            for row in rows['verses']:
                with st.container(border=True):
                    st.markdown(f"**{row['reference']}**")
                    st.write(row['text']);st.caption('Original form(s): '+row['forms'])
                    if st.button('Study this passage →',key=f"occurrence_{identity}_{row['book']}_{row['chapter']}_{row['verse']}"):
                        open_passage(row['reference'],source_label='Word occurrences')
            if not rows['verses']:st.info('No occurrences for this entry in the bundled edition.')
            with st.expander('Distribution by book'):st.dataframe(all_uses['books'],hide_index=True,width='stretch')
        except Exception as error:show_service_error(error)
    with personal:personal_notes=show_personal_notes('word_result',result)
    with details:
        st.markdown('Word data: [STEP Bible](https://www.stepbible.org/) · [Dataset and transformations](https://github.com/STEPBible/STEPBible-Data) · CC BY 4.0. Greek lexical definitions: TBESG. Hebrew glossary metadata: TBESH; full Hebrew definitions omitted. Occurrence previews: World English Bible via Bolls. Selected passage text uses the chosen version and its displayed provider/copyright notice.')
        st.caption('Greek occurrence index: TAGNT words marked NA28. Hebrew: TAHOT primary L/Q/R rows, excluding added X and alternate rows. References follow STEP English/NRSV numbering; WEB numbering and wording can differ in some passages. Counts can differ from Blue Letter Bible. See data/word_sources.json for file fingerprints and transformations.')
        with st.expander('Original lexical fields'):st.json(entry)
        notes=f"# Word study: {lexeme}\n\n{entry.get('transliteration','')} · Strong’s {entry.get('topic','')} · {entry.get('lemma_id','')}\n\n{clean(entry.get('short_definition'))}\n\n{clean(entry.get('definition'))}"
        if result.get('meaning_summary'):
            summary=result['meaning_summary']
            notes+='\n\n## Plain-language meaning\n\n'+summary['plain_meaning']
            if summary.get('contextual_meaning'):notes+='\n\n## Meaning in this passage\n\n'+summary['contextual_meaning']+'\n\n'+summary['why_this_meaning']
            notes+='\n\n'+summary.get('caution','')+'\n\nEvidence: '+', '.join(summary['references'])
        if result.get('passage_data',{}).get('selected'):
            notes+='\n\n## Selected passage ('+result['passage_data'].get('translation_code','WEB')+')\n\n'+'\n\n'.join(f"{r['reference']}: {r['text']}" for r in result['passage_data']['selected'])
            notes+='\n\n## Verified original forms\n\n'+'\n'.join(f"- {r['reference']}: {r['surface']} ({r['transliteration']}); gloss: {r['gloss']}; grammar: {r['morphology']}" for r in result['passage_data']['matches'])
        if result.get('word_guidance'):notes+='\n\n'+result['word_guidance']
        if result.get('passage_data',{}).get('copyright'):notes+='\n\n'+result['passage_data']['copyright']
        if personal_notes.strip():notes+='\n\n## My notes\n\n'+personal_notes
        notes+='\n\nSource: STEP Bible (https://www.stepbible.org/), CC BY 4.0. TAGNT/NA28 or TAHOT primary; WEB occurrence previews; selected passage version labeled above. AI explanations require review.'
        st.download_button('Download word study ↓',notes,file_name='word-study.md',mime='text/markdown')
        if st.button('Prepare occurrence list download',key='export_occurrences_'+identity):
            try:
                rows=occurrences(entry,limit=10000)
                import csv,io
                out=io.StringIO();writer=csv.DictWriter(out,fieldnames=['reference','forms','text']);writer.writeheader()
                writer.writerows({k:r[k] for k in writer.fieldnames} for r in rows['verses'])
                st.session_state['word_occurrence_export']={'identity':identity,'text':out.getvalue()}
            except Exception as error:show_service_error(error)
        exported=st.session_state.get('word_occurrence_export',{})
        if exported.get('identity')==identity:st.download_button('Download occurrences (CSV) ↓',exported['text'],file_name='word-occurrences.csv',mime='text/csv')
else:empty_state('word','A closer look at a familiar word.','Enter a word and a passage. Choose its Greek or Hebrew equivalent, then explore its meaning and uses.')

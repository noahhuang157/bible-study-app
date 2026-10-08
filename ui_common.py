"""Shared result layout, exports, and generation feedback."""
import re
import streamlit as st
from service_errors import show_service_error
from study_links import open_passage, open_word
from study_notes import show_personal_notes
from library_actions import persist_result, show_saved_actions
from advanced_ui import sermon_questions, related_panel


def download_text(result, personal_notes=""):
    text = f"# {result['label']}\n\n{result['text']}"
    if result.get("reader",{}).get("selected"):
        from bible_reader import reading_text
        text = f"# {result['label']}\n\n## Bible text ({result['reader']['translation']})\n\n" + reading_text(result["reader"]) + ("\n\n## Study background\n\n" + result.get("text", "") if result.get("text") else "")
    if result.get("reader",{}).get("copyright"):
        text += "\n\n" + result["reader"]["copyright"]
    if result.get("source_url"):
        text += f"\n\nOriginal sermon: {result['source_url']}"
    if "sources" in result:
        urls = [source["url"] for source in result["sources"] if source["retrieved"]]
        text += "\n\n## Source retrieval\n\n" + ("\n".join(urls) if urls else "No successful commentary retrieval reported; general AI-generated background.")
    if personal_notes.strip():
        text += f"\n\n## My notes\n\n{personal_notes}"
    if result.get('related_reading'):
        text += '\n\n## Suggested related reading\n\n'
        text += '\n\n'.join(f"**{p['reference']}** — {p['reason']}\n\nContext caution: {p['caution']}" for p in result['related_reading']['passages'])
    if result.get('qa_history'):
        text += '\n\n## Transcript questions\n\n'
        for qa in result['qa_history']:
            text += f"**{qa['question']}**\n\n{qa['answer']}\n\n"
            text += '\n\n'.join(f"> {e['quote']}" for e in qa['evidence']) + '\n\n'
    return text


def show_sources(result):
    if result.get("source_url"):
        st.link_button("Watch original sermon ↗", result["source_url"])
        st.caption("The notes are based on this video’s transcript.")
    if "sources" in result:
        sources = result["sources"]
        successful = [source for source in sources if source["retrieved"]]
        if successful:
            st.write("Commentary pages retrieved")
            for index, source in enumerate(successful, 1):
                st.link_button(f"Open commentary source {index} ↗", source["url"])
            st.caption("Retrieval does not verify each generated claim or confirm passage-specific coverage.")
        else:
            st.info("No successful commentary retrieval was reported. Treat this response as general AI-generated background, not a sourced commentary summary.")
        if any(not source["retrieved"] for source in sources):
            st.caption("At least one source retrieval attempt failed.")


def show_markdown_result(key, title):
    result = st.session_state.get(key)
    if not result:
        return
    st.markdown('<div class="result-meta">Your study notes</div>', unsafe_allow_html=True)
    st.subheader(result["label"])
    show_saved_actions(key, result)
    has_references = "references" in result
    if has_references:
        labels = ["Study notes", "Scripture mentions", "Ask this sermon", "My notes", "Sources & download"]
    elif key == 'topic_result':
        labels = ["Study notes", "Suggested reading", "My notes", "Sources & download"]
    else:
        labels = ["Study notes", "Word study", "Related passages", "My notes", "Sources & download"]
    tabs = st.tabs(labels)
    with tabs[0]:
        with st.container(border=True):
            text = result["text"]
            if has_references:
                # The full export retains mentions; the dedicated tab presents
                # them on screen so the main reading pane doesn't repeat them.
                text = re.sub(r"(?ms)^## Scripture mentions\n.*?(?=^## |\Z)", "", text)
            st.markdown(text)
    if has_references:
        with tabs[1]:
            references = result["references"]
            st.caption("Excerpts occur in the transcript. Reference labels and their usage descriptions are model-generated and still need checking.")
            if references:
                st.dataframe([{"Passage": r["reference"], "Use in sermon": r["usage"]} for r in references], hide_index=True, width="stretch")
                for index, mention in enumerate(references):
                    with st.expander(mention["reference"] + " · Transcript excerpt"):
                        st.write(mention["evidence"])
                        if st.button("Explore this passage →", key=f"reference_link_{index}"):
                            open_passage(mention["reference"], result.get("source_url", ""), result["label"])
            else:
                st.info("No supported explicit references were extracted. The sermon may still contain Scripture references.")
    elif key == 'topic_result':
        with tabs[1]:
            related_panel(key,result)
    else:
        with tabs[1]:
            st.subheader("Explore a word from this passage")
            st.caption(f"Passage: {result['label']}. Choose a word from the passage; Word Study checks its original-language matches. English words are not individually aligned to the tags.")
            with st.form("passage_word_link"):
                word = st.text_input("Word to explore", placeholder="love, agape, or G26")
                go = st.form_submit_button("Open Word Study →")
            if go:
                if word.strip():
                    open_word(word.strip(), result["label"])
                else:
                    st.warning("Enter a word to explore first.")
    if has_references:
        with tabs[2]:
            sermon_questions(result)
    elif key != 'topic_result':
        with tabs[2]:
            related_panel(key,result)
    with tabs[-2]:
        personal_notes = show_personal_notes(key, result)
    with tabs[-1]:
        show_sources(result)
        st.divider()
        st.subheader("Keep a copy")
        st.write("Download your complete notes as a Markdown file to read or edit later.")
        filename = re.sub(r"[^a-zA-Z0-9_-]+", "-", result["label"]).strip("-")[:80]
        st.download_button("Download study notes ↓", download_text(result, personal_notes),
                           file_name=f"{filename or title}.md", mime="text/markdown")
        st.caption("Download an additional copy to keep or edit outside the app.")


def generate_result(key, label, action):
    try:
        with st.spinner("Preparing your study…"):
            payload = action()
        result = payload if isinstance(payload, dict) else {"text": payload}
        if not result.get("text"):
            raise ValueError("No content was returned. Please try again.")
        st.session_state[key] = {**result, "label": label}
        persist_result(key, st.session_state[key])
        st.success("Your study is ready below.")
    except ValueError as error:
        st.warning(str(error))
    except Exception as error:
        show_service_error(error, has_previous=bool(st.session_state.get(key)))

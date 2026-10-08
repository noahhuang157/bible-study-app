"""Shared translation choices and publisher/provider attribution."""
import json
from html import escape
from urllib.parse import urlparse
import re
import streamlit as st
from translations import TRANSLATIONS


def translation_picker(key):
    st.session_state.setdefault(key,st.session_state.get('bible_translation','WEB'))
    code=st.selectbox('Bible version',list(TRANSLATIONS),format_func=lambda c:f'{c} · {TRANSLATIONS[c]}',key=key)
    st.caption('WEB is available offline. The other versions use your configured Bible provider access.')
    return code


def show_attribution(reading):
    if reading.get('copyright'):st.caption(reading['copyright'])
    if reading.get('provider')=='API.Bible':
        st.markdown('Bible text provided by [API.Bible](https://api.bible).')
        import streamlit.components.v1 as components
        meta=reading.get('provider_meta',{})
        token=meta.get('fumsToken')
        if token:
            literal=json.dumps(token).replace('<','\\u003c')
            components.html('<script>window.fumsData=[];window.fums=function(){window.fumsData.push(arguments);};</script><script src="https://pkg.api.bible/fumsV3.min.js"></script><script>fums("trackView",'+literal+');</script>',height=0)
        elif meta.get('fumsNoScript'):
            # Legacy response: use only the provider's tracking image, never arbitrary scripts.
            match=re.search(r'src=[\"\']([^\"\']+)',meta['fumsNoScript'])
            target=('https:'+match[1] if match[1].startswith('//') else match[1]) if match else ''
            if urlparse(target).scheme=='https' and urlparse(target).hostname=='fums.api.bible':
                components.html('<img alt="" src="'+escape(target,quote=True)+'"/>',height=0)

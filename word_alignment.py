"""Render attested token/gloss pairs, never infer English-prose alignment."""
from html import escape


def aligned_html(tokens, hebrew=False):
    cells=[]
    for token in tokens:
        marked=bool(token.get('matched'))
        tag='mark' if marked else 'span'
        original=escape(token.get('surface',''))
        gloss=escape(token.get('gloss','') or '—')
        cells.append(f'<{tag} class="aligned-token"><span class="aligned-original" dir="'+('rtl' if hebrew else 'ltr')+f'">{original}</span><span class="aligned-gloss" dir="ltr">{gloss}</span></{tag}>')
    return '<div class="aligned-verse" dir="'+('rtl' if hebrew else 'ltr')+'">'+''.join(cells)+'</div>'

from transcript import get_transcript
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_video_id(youtube_link):
    from urllib.parse import urlparse, parse_qs
    import re

    parsed = urlparse(youtube_link.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("https", "http"):
        raise ValueError("Enter a full YouTube URL starting with https://.")
    if host in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.strip("/")
    elif host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        parts = parsed.path.strip("/").split("/")
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif len(parts) == 2 and parts[0] in ("shorts", "embed", "live"):
            video_id = parts[1]
        else:
            video_id = ""
    else:
        video_id = ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Enter a valid YouTube video link, not a channel or playlist link.")
    return video_id


def build_prompt(text, format_choice):
    from prompts.sermon import build_sermon_prompt
    return build_sermon_prompt(text, format_choice)


def call_gemini(prompt):
    from google.genai.types import GenerateContentConfig
    from study_models import SermonStudy
    if not GEMINI_API_KEY:
        raise ValueError("Add GEMINI_API_KEY to your .env file, then restart Streamlit.")
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        contents=prompt,
        config=GenerateContentConfig(
            response_mime_type="application/json", response_schema=SermonStudy,
        ),
    )
    if not response.text:
        raise ValueError("The model returned no study notes. Try again or check your Gemini model setting.")
    return response.text


def normalize_evidence(text):
    import re
    import unicodedata
    # Ignore capitalization and whitespace differences, but retain punctuation
    # and wording so invented or rewritten evidence does not pass this check.
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().casefold()


def parse_study(raw, transcript, format_choice):
    from pydantic import ValidationError
    from study_models import SermonStudy
    try:
        study = SermonStudy.model_validate_json(raw)
    except ValidationError:
        raise ValueError("The model returned an incomplete or invalid study format. Please try again.") from None
    if not study.sections or any(not s.title.strip() or not s.items or any(not i.strip() for i in s.items) for s in study.sections):
        raise ValueError("The model returned empty study sections. Please try again.")
    if format_choice == "2" and [s.title for s in study.sections] != ["Observation", "Interpretation", "Application"]:
        raise ValueError("The model did not return the three inductive study stages. Please try again.")
    source = normalize_evidence(transcript)
    mentions = []
    seen = set()
    dropped = False
    for mention in study.scripture_references:
        evidence = normalize_evidence(mention.evidence)
        reference = normalize_evidence(mention.reference)
        if not reference or not evidence or evidence not in source:
            dropped = True
            continue
        if reference not in seen:
            mentions.append(mention)
            seen.add(reference)
    study.scripture_references = mentions
    verified_quotes = [q for q in study.quotes if normalize_evidence(q) and normalize_evidence(q) in source]
    if len(verified_quotes) != len(study.quotes):
        dropped = True
    study.quotes = verified_quotes[:3]
    if dropped:
        study.limitations.append("Some model-proposed references or quotations were omitted because their exact supporting excerpt was not found in the transcript.")
    return study


def render_study(study, format_choice):
    mode = "Structured Notes" if format_choice == "1" else "Inductive Study"
    lines = [f"## Sermon overview · {mode}",
             f"**Speaker:** {study.overview.speaker}",
             f"**Main passage:** {study.overview.main_passage}",
             f"**Central message:** {study.overview.central_message}"]
    for section in study.sections:
        lines.append(f"## {section.title}")
        lines.extend(f"- {item}" for item in section.items)
    for heading, items in [("Key takeaways", study.key_takeaways),
                           ("Questions for reflection · generated prompts", study.reflection_questions)]:
        lines.append(f"## {heading}")
        lines.extend(f"- {item}" for item in items)
    if study.quotes:
        lines.append("## Transcript quotations")
        lines.extend(f"> {q}" for q in study.quotes)
    lines.append("## Scripture mentions")
    if not study.scripture_references:
        lines.append("No supported explicit references were extracted. This does not prove that the sermon contains no Scripture references.")
    for mention in study.scripture_references:
        lines.extend([f"**{mention.reference}** — {mention.usage}", f"> {mention.evidence}"])
    if study.limitations:
        lines.append("## Notes and limitations")
        lines.extend(f"- {item}" for item in study.limitations)
    return "\n\n".join(lines)


def get_sermon_study(youtube_link, format_choice):
    if format_choice not in ("1", "2"):
        raise ValueError("Choose Structured Notes or Inductive Study.")
    video_id = get_video_id(youtube_link)
    if not GEMINI_API_KEY:
        raise ValueError("Add GEMINI_API_KEY to your .env file, then restart Streamlit.")
    text = get_transcript(video_id)
    if not text.strip():
        raise ValueError("No transcript was found for this video.")
    study = parse_study(call_gemini(build_prompt(text, format_choice)), text, format_choice)
    return {"text": render_study(study, format_choice),
            "references": [r.model_dump() for r in study.scripture_references],
            "transcript": text,
            "source_url": f"https://www.youtube.com/watch?v={video_id}"}


def get_summary(youtube_link, format_choice):
    """Keep the original string-returning function available for other scripts."""
    return get_sermon_study(youtube_link, format_choice)["text"]

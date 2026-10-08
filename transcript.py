import requests
import os
from dotenv import load_dotenv

load_dotenv()
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


def get_transcript(video_id):
    if not SERPAPI_API_KEY:
        raise ValueError("Add SERPAPI_API_KEY to your .env file, then restart Streamlit.")
    params = {
        "api_key": SERPAPI_API_KEY,
        "engine": "youtube_video_transcript",
        "v": video_id,
        "type": "asr"
    }
    search = requests.get("https://serpapi.com/search", params=params, timeout=30)
    search.raise_for_status()
    response = search.json()
    if response.get("error"):
        raise ValueError("The transcript provider could not retrieve this video. Check transcript availability and your SerpAPI quota.")
    text = " ".join(item.get("snippet", "") for item in response.get("transcript", []))
    if not text.strip():
        raise ValueError("No transcript was found for this video. Try another sermon.")
    return text
"""Validate Gemini's output before the page tries to display it."""
from pydantic import BaseModel, Field


class SermonOverview(BaseModel):
    speaker: str
    main_passage: str
    central_message: str


class StudySection(BaseModel):
    title: str
    items: list[str]


class ScriptureMention(BaseModel):
    reference: str
    usage: str
    evidence: str = Field(description="Exact transcript excerpt containing the explicit reference")


class SermonStudy(BaseModel):
    overview: SermonOverview
    sections: list[StudySection]
    key_takeaways: list[str]
    reflection_questions: list[str]
    scripture_references: list[ScriptureMention]
    quotes: list[str]
    limitations: list[str]

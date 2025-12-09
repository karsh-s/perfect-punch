from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI
import os

router = APIRouter(prefix="/session", tags=["feedback"])

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SessionData(BaseModel):
    summary: dict
    punches: list

@router.post("/feedback")
async def generate_feedback(session: SessionData):
    prompt = f"""
    You are a professional boxing coach. Analyze this punch session:
    {session.json()}

    Provide:
    - Performance summary
    - Strengths
    - Weaknesses
    - Specific improvement advice
    - Motivation
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a boxing coach."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return {"feedback": response.choices[0].message["content"]}

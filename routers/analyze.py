from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, re
import httpx

router = APIRouter()

class AnalyzeRequest(BaseModel):
    prompt: str

@router.post("/")
async def analyze_sentiment(payload: AnalyzeRequest):
    api_key = os.getenv("GENERATIVE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(500, "API key not set")

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
    body = {"contents":[{"role":"user","parts":[{"text":payload.prompt}]}]}

    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            headers={
                "Content-Type":"application/json",
                "x-goog-api-key": api_key
            },
            json=body
        )
    if not r.is_success:
        # on error, mirror your Next.js behavior: return “50”
        return "50"

    data = r.json()
    text = (
        data
        .get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )
    m = re.search(r"\d{1,3}", text)
    score = int(m.group()) if m else 50
    score = max(0, min(100, score))
    return str(score)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os, httpx
from datetime import datetime

router = APIRouter()

class Msg(BaseModel):
    from_: str = Field(..., alias="from")
    date: str
    body: str

class SummReq(BaseModel):
    messages: list[Msg]

@router.post("/")
async def summarize(req: SummReq):
    if not req.messages:
        raise HTTPException(400, "No messages to summarize")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(500, "API key missing")

    snippets = []
    for m in req.messages[:100]:
        dt = datetime.fromisoformat(m.date).strftime("%Y-%m-%d %H:%M:%S")
        snippets.append(f"FROM: {m.from_}\nDATE: {dt}\nMESSAGE:\n{m.body}")
    thread = "\n\n---\n\n".join(snippets)

    prompt = (
        "Summarize the following email conversation in 3–5 bullet points.\n"
        "Focus on the key points, actions, and requests. Use Japanese. "
        "Return in plain text format and use ・ for bullet points.\n\n"
        f"{thread}"
    )

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
    body = {"contents":[{"role":"user","parts":[{"text":prompt}]}]}

    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            headers={"Content-Type":"application/json","x-goog-api-key":api_key},
            json=body
        )
    data = r.json()
    summary = (
        data.get("candidates",[{}])[0]
            .get("content",{})
            .get("parts",[{}])[0]
            .get("text","No summary available.")
    )
    return {"summary": summary}

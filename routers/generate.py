from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import os, httpx

router = APIRouter()

class Msg(BaseModel):
    from_: str = Field(..., alias="from")
    date: str
    body: str

class GenerateRequest(BaseModel):
    instruction: str
    threadId: str
    messages: list[Msg] = []

@router.post("/")
async def generate_email(req: GenerateRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(500, "API key missing")

    # build thread context
    thread_content = ""
    if req.messages:
        parts = []
        for m in req.messages:
            dt = datetime.fromisoformat(m.date).strftime("%Y-%m-%d %H:%M:%S")
            parts.append(f"FROM: {m.from_}\nDATE: {dt}\nMESSAGE:\n{m.body}")
        thread_content = "\n\n---\n\n".join(parts)

    prompt = (
        "You are composing a professional reply to the following email."
        + (f"\n\nEmail thread:\n{thread_content}\n\n" if thread_content else "")
        + "Please consider the context and write a response based on the instruction below.\n"
        "The reply must:\n"
        "- Match the language used in the original email (Japanese or English)\n"
        "- Maintain a professional and respectful tone\n"
        "- Address the sender by name if available\n"
        "- Include no extra explanations—just the reply content\n"
        + f"\n\nUser instruction: \"{req.instruction}\"\n\n"
        "Write the email reply below:\n"
    )

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    body = {"contents":[{"role":"user","parts":[{"text":prompt}]}]}

    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            headers={"Content-Type":"application/json","x-goog-api-key":api_key},
            json=body
        )
    if not r.is_success:
        raise HTTPException(500, "Generation failed")

    data = r.json()
    gen = (
        data.get("candidates",[{}])[0]
            .get("content",{})
            .get("parts",[{}])[0]
            .get("text","")
            .strip()
    )
    return {"response": gen}

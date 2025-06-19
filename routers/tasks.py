from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os, re, httpx

router = APIRouter()

class Msg(BaseModel):
    threadId: str
    from_: str = Field(..., alias="from")
    subject: str = ""
    body: str

class TaskReq(BaseModel):
    messages: list[Msg]

@router.post("/")
async def extract_tasks(req: TaskReq):
    msgs = [
        m
        for m in req.messages
        if not re.search(r"(no-reply|noreply|promo|newsletter|feedback)", m.from_, re.I)
        and not re.search(r"(promo|unsubscribe|verify|reset)", m.subject, re.I)
    ]

    if not msgs:
        return {"tasks": []}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(500, "API key missing")

    parts = []
    for m in msgs:
        parts.append(f"MESSAGE (THREAD_ID: {m.threadId}):\n{m.body}")
    thread = "\n\n---\n\n".join(parts)

    prompt = (
        "Extract tasks from the following email messages.  \n"
        "Each message is labeled with its THREAD_ID. "
        "Use same language as message. "
        "For each task return JSON with keys: task, date, time, threadId.  \n"
        "Put those with both date+time first (earliest→latest), then date-only. "
        "Return _only_ the JSON array.\n\n"
        f"{thread}"
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
        raise HTTPException(502, "Gemini API error")

    raw = r.json().get("candidates",[{}])[0] \
           .get("content",{}).get("parts",[{}])[0] \
           .get("text","").strip()
    # strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*|```$", "", raw).strip()

    try:
        tasks = __import__("json").loads(raw)
    except Exception:
        raise HTTPException(500, "Failed to parse tasks JSON")

    return {"tasks": tasks}

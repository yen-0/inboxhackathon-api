from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware
import os

from routers import auth, analyze, generate, summarize, tasks

app = FastAPI(title="Embox API")
@app.get("/", response_class=PlainTextResponse)
async def health_check():
    return "OK"
# This secret is used to sign the session cookie in auth.py
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "CHANGE_ME"))

# mount routers
app.include_router(auth.router,    prefix="/auth",              tags=["auth"])
app.include_router(analyze.router, prefix="/analyze-sentiment", tags=["analysis"])
app.include_router(generate.router,prefix="/generate",           tags=["generation"])
app.include_router(summarize.router,prefix="/summarize",         tags=["summarization"])
app.include_router(tasks.router,   prefix="/tasks",              tags=["tasks"])
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
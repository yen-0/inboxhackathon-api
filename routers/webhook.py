import os
import json
import asyncio
import base64
import httpx

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Shared in-memory token store (imported from auth module)
from routers.auth import user_tokens
# AI utility functions
from routers.analyze import AnalyzeRequest, analyze_sentiment
from routers.generate import GenerateRequest, generate_email
from routers.summarize import SummReq, Msg as SummMsg, summarize
from routers.tasks import TaskReq, Msg as TaskMsg, extract_tasks

# FastAPI router
router = APIRouter()

# LINE SDK setup
LINE_TOKEN = os.getenv("LINE_CHANNEL_TOKEN")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET")
if not LINE_TOKEN or not LINE_SECRET:
    raise RuntimeError("LINE_CHANNEL_TOKEN and LINE_CHANNEL_SECRET must be set")

line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)


def fetch_recent_emails(access_token: str, max_results: int = 3):
    creds = Credentials(token=access_token)
    service = build("gmail", "v1", credentials=creds)
    msgs_resp = service.users().messages().list(userId="me", maxResults=max_results).execute()
    out = []
    for m in msgs_resp.get("messages", []):
        full = service.users().messages().get(
            userId="me", id=m["id"], format="full"
        ).execute()
        headers = {h["name"].lower(): h["value"] for h in full["payload"]["headers"]}
        body = ""
        for part in full["payload"].get("parts", []):
            if part.get("mimeType", "").startswith("text/"):
                data = part["body"].get("data") or ""
                body = base64.urlsafe_b64decode(data.encode()).decode()
                break
        out.append({
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "body": body,
        })
    return out

# Webhook endpoint for LINE
@router.post("/webhook")
async def line_webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return PlainTextResponse("OK")

# Process LINE events asynchronously
async def process_event(event):
    text = event.message.text.strip()
    reply_token = event.reply_token
    parts = text.split(" ", 1)
    cmd = parts[0].lstrip("/").lower()
    arg = parts[1] if len(parts) > 1 else ""

    # /recent or /mail command: fetch Gmail and analyze sentiment in parallel
    if cmd in ("recent", "mail"):
        line_id = event.source.user_id
        access_token = user_tokens.get(line_id)
        if not access_token:
            login_url = f"{os.getenv('API_BASE_URL')}/auth/login?userId={line_id}"
            return line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=f"まずはGmail認証が必要です: {login_url}")
            )
        emails = fetch_recent_emails(access_token)
        # Launch sentiment analysis tasks concurrently
        tasks = [analyze_sentiment(AnalyzeRequest(prompt=e["body"])) for e in emails]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        replies = []
        for e, res in zip(emails, results):
            if isinstance(res, Exception):
                if isinstance(res, httpx.ReadTimeout):
                    score_text = "解析タイムアウト"
                else:
                    score_text = f"解析エラー: {res}"
            else:
                score_text = str(res)
            replies.append(f"{e['from']}／{e['subject']} → {score_text}")

        return line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="\n".join(replies))
        )

    # /analyze command
    if cmd == "analyze" and arg:
        try:
            score = await analyze_sentiment(AnalyzeRequest(prompt=arg))
            reply = f"Sentiment score: {score}"
        except Exception as e:
            reply = f"解析失敗: {e}"
        return line_bot_api.reply_message(reply_token, TextSendMessage(text=reply))

    # /generate command
    if cmd == "generate" and arg:
        try:
            res = await generate_email(
                GenerateRequest(instruction=arg, threadId="LINE", messages=[])
            )
            reply = res.get("response", "")
        except Exception as e:
            reply = f"生成失敗: {e}"
        return line_bot_api.reply_message(reply_token, TextSendMessage(text=reply))

    # /summarize command
    if cmd == "summarize" and arg:
        try:
            msgs = json.loads(arg)
            msg_objs = [SummMsg(**m) for m in msgs]
            res = await summarize(SummReq(messages=msg_objs))
            reply = res.get("summary", "")
        except Exception as e:
            reply = f"要約失敗: {e}"
        return line_bot_api.reply_message(reply_token, TextSendMessage(text=reply))

    # /tasks command
    if cmd == "tasks" and arg:
        try:
            msgs = json.loads(arg)
            msg_objs = [TaskMsg(**m) for m in msgs]
            res = await extract_tasks(TaskReq(messages=msg_objs))
            tasks_list = res.get("tasks", [])
            if not tasks_list:
                reply = "タスクが見つかりませんでした。"
            else:
                reply = "\n".join([f"・{t['task']} ({t['date']} {t.get('time','')})" for t in tasks_list])
        except Exception as e:
            reply = f"タスク抽出失敗: {e}"
        return line_bot_api.reply_message(reply_token, TextSendMessage(text=reply))

    # Default help message
    help_text = (
        "使い方:\n"
        "/analyze [テキスト] → 感情分析\n"
        "/generate [指示] → メール生成\n"
        "/summarize [JSON messages] → 要約\n"
        "/tasks [JSON messages] → タスク抽出\n"
        "/recent → 最新メールを取得し感情分析"
    )
    return line_bot_api.reply_message(reply_token, TextSendMessage(text=help_text))

# Register handler to dispatch events
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    asyncio.create_task(process_event(event))

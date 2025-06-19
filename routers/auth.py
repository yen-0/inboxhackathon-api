from fastapi import APIRouter, Request, HTTPException
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import os

config = Config(".env")  # for local dev; in Cloud Run use env vars
oauth = OAuth(config)
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email "
                 "https://www.googleapis.com/auth/gmail.readonly "
                 "https://www.googleapis.com/auth/gmail.send"
    },
)

router = APIRouter()

@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    if not token:
        raise HTTPException(400, "Google authorization failed")
    user = await oauth.google.parse_id_token(request, token)
    # store in session
    request.session["user"] = user
    request.session["access_token"] = token["access_token"]
    return RedirectResponse("/")  # or wherever your front-end lives

@router.get("/session")
async def get_session(request: Request):
    if "user" not in request.session:
        raise HTTPException(401, "Not logged in")
    return {
        "user": request.session["user"],
        "access_token": request.session["access_token"],
    }

@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "logged out"}

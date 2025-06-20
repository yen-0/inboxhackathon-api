import os, traceback
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# ------------------------------------------------------------------
# In-memory store for LINE user → Gmail access_token
# (swap out for a real DB in production)
user_tokens: dict[str, str] = {}
# ------------------------------------------------------------------

# Authlib setup (reads CLIENT_ID/SECRET from env or .env)
config = Config(".env")
oauth = OAuth(config)
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": (
            "openid email "
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/gmail.send"
        )
    },
)

router = APIRouter()

@router.get("/login")
async def login(request: Request, userId: str):
    """
    Kick off Google OAuth, tagging the request with `state=userId`
    so we know which LINE user is completing the flow.
    """
    base = os.getenv("API_BASE_URL")
    redirect_uri = f"{base}/auth/callback"
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        state=userId,
    )

@router.get("/callback")
async def auth_callback(request: Request):
    """
    Handle Google’s redirect.  Exchange code→token, fetch profile,
    then stash access_token in user_tokens[line_user_id].
    """
    try:
        token = await oauth.google.authorize_access_token(request)
        if not token or "access_token" not in token:
            raise HTTPException(400, "Google authorization failed")

        # Always fetch userinfo
        resp = await oauth.google.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            token={"access_token": token["access_token"]}
        )
        resp.raise_for_status()
        user_profile = resp.json()

        # Extract LINE userId from state
        line_user_id = request.query_params.get("state")
        if not line_user_id:
            raise HTTPException(400, "Missing state (LINE user ID)")

        # Persist access_token
        user_tokens[line_user_id] = token["access_token"]

        # (Optional) You can also store user_profile in a DB here

        # Done — send them back to wherever your front-end is
        return RedirectResponse("/")

    except Exception as e:
        tb = traceback.format_exc()
        return PlainTextResponse(
            f"🚨 Callback error:\n{e}\n\nTraceback:\n{tb}",
            status_code=500
        )

@router.get("/session")  # (Still here if you need browser sessions)
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

# ---------------------------------------------------------------
# In your LINE webhook handler, look up the token like:
#
#   token = user_tokens.get(event.source.user_id)
#   if not token:
#     # ask them to /login with their LINE userId:
#     login_url = f"{os.getenv('API_BASE_URL')}/auth/login?userId={event.source.user_id}"
#     …
# ---------------------------------------------------------------

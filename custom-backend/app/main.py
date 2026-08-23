import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr

from .database import (
    ensure_demo_users,
    get_file_by_id,
    get_user_by_email,
    get_user_by_id,
    init_db,
    list_files_for_user,
    create_user,
    verify_password,
)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

init_db()
ensure_demo_users()

app = FastAPI(title="Osdag Secure Auth API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REVOKED_TOKENS = set()
FAILED_ATTEMPTS = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 60


class RegisterPayload(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


class FileMetadataResponse(BaseModel):
    id: str
    user_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    uploaded_at: str


def create_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expires_at.timestamp()}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_bearer_token(authorization: Annotated[str | None, Header(alias="Authorization")]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    if token in REVOKED_TOKENS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user_id = payload.get("sub")
    if not user_id or not get_user_by_id(user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return token


def get_current_user_id(token: Annotated[str, Depends(get_bearer_token)]) -> str:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload["sub"]


def enforce_login_lockout(email: str) -> None:
    entry = FAILED_ATTEMPTS.get(email)
    if entry and entry.get("locked_until") and entry["locked_until"] > datetime.now().timestamp():
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed attempts. Try again in a bit.")


def record_failed_login(email: str) -> None:
    entry = FAILED_ATTEMPTS.get(email, {"count": 0, "locked_until": 0})
    entry["count"] += 1
    if entry["count"] >= MAX_FAILED_ATTEMPTS:
        entry["locked_until"] = (datetime.now() + timedelta(seconds=LOCKOUT_SECONDS)).timestamp()
        entry["count"] = 0
    FAILED_ATTEMPTS[email] = entry


def clear_failed_login(email: str) -> None:
    FAILED_ATTEMPTS.pop(email, None)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    ensure_demo_users()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/register")
def register(payload: RegisterPayload):
    email = payload.email.lower().strip()
    password = payload.password.strip()
    name = (payload.name or email.split("@")[0]).strip()

    if not email or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email and password are required")

    if get_user_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists")

    user = create_user(email, password, name)
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


@app.post("/api/login")
def login(payload: LoginPayload):
    email = payload.email.lower().strip()
    password = payload.password

    enforce_login_lockout(email)
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        record_failed_login(email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    clear_failed_login(email)
    token = create_token(user["id"])
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "name": user["name"]}}


@app.post("/api/logout")
def logout(token: Annotated[str, Depends(get_bearer_token)]):
    REVOKED_TOKENS.add(token)
    return {"message": "Logged out"}


@app.get("/api/user")
def get_user(current_user_id: Annotated[str, Depends(get_current_user_id)]):
    user = get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


@app.get("/api/files")
def list_user_files(current_user_id: Annotated[str, Depends(get_current_user_id)]):
    rows = list_files_for_user(current_user_id)
    return {"files": rows}


@app.get("/api/files/{file_id}")
def get_single_file(file_id: str, current_user_id: Annotated[str, Depends(get_current_user_id)]):
    file_record = get_file_by_id(file_id)
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if file_record["user_id"] != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this file")
    return file_record


@app.get("/api/files/{file_id}/download")
def download_file(file_id: str, current_user_id: Annotated[str, Depends(get_current_user_id)]):
    file_record = get_file_by_id(file_id)
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if file_record["user_id"] != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this file")

    file_path = file_record["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")

    return FileResponse(
        path=file_path,
        filename=file_record["file_name"],
        media_type=file_record["mime_type"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("APP_PORT", "8000")), reload=True)

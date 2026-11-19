"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
TEACHER_CREDENTIALS_PATH = current_dir / "teachers.json"
SESSION_COOKIE_NAME = "teacher_session"
SESSION_LIFETIME_SECONDS = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000
SESSION_SECRET = os.environ.get("SESSION_SECRET", "").encode("utf-8")
if not SESSION_SECRET:
    SESSION_SECRET = secrets.token_bytes(32)
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "").lower() in {
    "1", "true", "yes"
}

app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


class LoginRequest(BaseModel):
    username: str
    password: str


def hash_teacher_password(password: str) -> dict[str, str | int]:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return {
        "salt": salt.hex(),
        "password_hash": password_hash.hex(),
        "iterations": PASSWORD_HASH_ITERATIONS,
    }


def verify_teacher_password(password: str, record: dict[str, object]) -> bool:
    try:
        salt = bytes.fromhex(record["salt"])
        expected_hash = bytes.fromhex(record["password_hash"])
        iterations = record["iterations"]
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=500, detail="Teacher credentials are incorrectly configured."
        )

    if not isinstance(iterations, int) or iterations < 1:
        raise HTTPException(
            status_code=500, detail="Teacher credentials are incorrectly configured."
        )

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def load_teacher_accounts() -> dict[str, dict[str, object]]:
    try:
        credentials = json.loads(TEACHER_CREDENTIALS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts are not configured. See the setup instructions.",
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Teacher credentials are not valid JSON."
        )

    accounts = credentials.get("teachers") if isinstance(credentials, dict) else None
    if not isinstance(accounts, dict):
        raise HTTPException(
            status_code=500,
            detail="Teacher credentials must contain a teachers object.",
        )
    return accounts


def create_session_token(username: str) -> str:
    payload = json.dumps(
        {"username": username, "expires": int(time.time()) + SESSION_LIFETIME_SECONDS},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        SESSION_SECRET, encoded_payload.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def get_session_username(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    try:
        encoded_payload, signature = token.split(".", 1)
        expected_signature = hmac.new(
            SESSION_SECRET, encoded_payload.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return None

        payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        session = json.loads(payload)
        username = session["username"]
        expires = session["expires"]
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        return None

    if not isinstance(username, str) or not isinstance(expires, int):
        return None
    if expires <= time.time():
        return None
    return username


def require_teacher(request: Request) -> str:
    username = get_session_username(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher sign-in required.")
    return username


@app.get("/auth/session")
def get_auth_session(request: Request):
    username = get_session_username(request)
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/login")
def login(credentials: LoginRequest, response: Response):
    accounts = load_teacher_accounts()
    record = accounts.get(credentials.username)
    if not isinstance(record, dict) or not verify_teacher_password(
        credentials.password, record
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(credentials.username),
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"message": "Signed in", "username": credentials.username}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"message": "Signed out"}


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, email: str, _teacher: str = Depends(require_teacher)
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _teacher: str = Depends(require_teacher)
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}

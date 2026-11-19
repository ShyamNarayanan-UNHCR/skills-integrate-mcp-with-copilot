import json
from getpass import getpass

from app import TEACHER_CREDENTIALS_PATH, hash_teacher_password


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty.")

    password = getpass("Assigned password (12+ characters): ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")

    if TEACHER_CREDENTIALS_PATH.exists():
        credentials = json.loads(
            TEACHER_CREDENTIALS_PATH.read_text(encoding="utf-8")
        )
        teachers = credentials.get("teachers") if isinstance(credentials, dict) else None
        if not isinstance(teachers, dict):
            raise SystemExit("Teacher credentials must contain a teachers object.")
    else:
        teachers = {}

    teachers[username] = hash_teacher_password(password)
    TEACHER_CREDENTIALS_PATH.write_text(
        json.dumps({"teachers": teachers}, indent=2) + "\n", encoding="utf-8"
    )
    TEACHER_CREDENTIALS_PATH.chmod(0o600)
    print(f"Teacher account saved for {username}.")


if __name__ == "__main__":
    main()

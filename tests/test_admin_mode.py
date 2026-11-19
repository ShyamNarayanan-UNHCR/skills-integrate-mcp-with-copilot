import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException, Response
from fastapi.routing import APIRoute

import src.app as app_module


class AdminModeTests(unittest.TestCase):
    def test_password_hash_verifies_only_the_original_password(self):
        record = app_module.hash_teacher_password("correct horse battery")

        self.assertTrue(
            app_module.verify_teacher_password("correct horse battery", record)
        )
        self.assertFalse(app_module.verify_teacher_password("wrong password", record))

    def test_session_rejects_tampered_and_expired_tokens(self):
        token = app_module.create_session_token("teacher")
        request = SimpleNamespace(
            cookies={app_module.SESSION_COOKIE_NAME: token}
        )
        self.assertEqual(app_module.get_session_username(request), "teacher")

        request.cookies[app_module.SESSION_COOKIE_NAME] = token.rsplit(".", 1)[0] + "." + "0" * 64
        self.assertIsNone(app_module.get_session_username(request))

        with patch("src.app.time.time", return_value=0):
            expired_token = app_module.create_session_token("teacher")
        request.cookies[app_module.SESSION_COOKIE_NAME] = expired_token
        with patch(
            "src.app.time.time",
            return_value=app_module.SESSION_LIFETIME_SECONDS + 1,
        ):
            self.assertIsNone(app_module.get_session_username(request))

    def test_login_sets_http_only_signed_cookie(self):
        with tempfile.TemporaryDirectory() as directory:
            credentials_path = Path(directory) / "teachers.json"
            credentials_path.write_text(
                json.dumps(
                    {
                        "teachers": {
                            "teacher": app_module.hash_teacher_password(
                                "correct horse battery"
                            )
                        }
                    }
                ),
                encoding="utf-8",
            )
            response = Response()

            with patch.object(
                app_module, "TEACHER_CREDENTIALS_PATH", credentials_path
            ):
                result = app_module.login(
                    app_module.LoginRequest(
                        username="teacher", password="correct horse battery"
                    ),
                    response,
                )

            self.assertEqual(result["username"], "teacher")
            self.assertIn("teacher_session=", response.headers["set-cookie"])
            self.assertIn("httponly", response.headers["set-cookie"].lower())

    def test_activity_mutations_require_teacher_dependency(self):
        protected_routes = {
            (route.path, method): route
            for route in app_module.app.routes
            if isinstance(route, APIRoute)
            for method in route.methods or []
            if method in {"POST", "DELETE"}
        }

        for path, method in (
            ("/activities/{activity_name}/signup", "POST"),
            ("/activities/{activity_name}/unregister", "DELETE"),
        ):
            route = protected_routes[(path, method)]
            self.assertTrue(
                any(
                    dependency.call is app_module.require_teacher
                    for dependency in route.dependant.dependencies
                )
            )

    def test_missing_session_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            app_module.require_teacher(SimpleNamespace(cookies={}))

        self.assertEqual(error.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()

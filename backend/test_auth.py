import unittest
import os
from unittest.mock import patch

os.environ.setdefault("FLASK_SECRET_KEY", "test-only-secret-key")

from werkzeug.security import check_password_hash

import app


class FakeDatabase:
    def __init__(self):
        self.users = {}

    def connect(self):
        return FakeConnection(self.users)


class FakeConnection:
    def __init__(self, users):
        self.users = users

    def cursor(self, dictionary=False):
        return FakeCursor(self.users)

    def commit(self):
        pass

    def close(self):
        pass


class FakeCursor:
    def __init__(self, users):
        self.users = users
        self.result = None
        self.lastrowid = None

    def execute(self, query, params=()):
        normalized_query = " ".join(query.split()).lower()

        if normalized_query.startswith("select id from users where email"):
            self.result = next(
                ({"id": user["id"]} for user in self.users.values()
                 if user["email"] == params[0]),
                None,
            )
        elif normalized_query.startswith("insert into users"):
            name, email, password_hash, role = params
            user_id = len(self.users) + 1
            self.users[email] = {
                "id": user_id,
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "role": role,
            }
            self.lastrowid = user_id
            self.result = None
        elif "password_hash" in normalized_query:
            self.result = next(
                (user.copy() for user in self.users.values()
                 if user["email"] == params[0]),
                None,
            )
        elif normalized_query.startswith("select id, name, email, role"):
            self.result = next(
                (
                    {
                        "id": user["id"],
                        "name": user["name"],
                        "email": user["email"],
                        "role": user["role"],
                    }
                    for user in self.users.values()
                    if user["id"] == params[0]
                ),
                None,
            )
        else:
            raise AssertionError(f"Unexpected SQL in auth test: {query}")

    def fetchone(self):
        return self.result

    def close(self):
        pass


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase()
        self.connection_patch = patch(
            "app.get_db_connection",
            side_effect=self.database.connect,
        )
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)
        self.client = app.app.test_client()

    def test_register_creates_hashed_user(self):
        response = self.client.post(
            "/api/register",
            json={
                "name": "Test Student",
                "email": "Student@Example.com",
                "password": "test-password",
                "role": "student",
            },
        )

        self.assertEqual(response.status_code, 201)
        user = self.database.users["student@example.com"]
        self.assertEqual(user["name"], "Test Student")
        self.assertTrue(check_password_hash(user["password_hash"], "test-password"))

    def test_register_rejects_duplicate_email(self):
        self.database.users["student@example.com"] = {
            "id": 1,
            "name": "Existing Student",
            "email": "student@example.com",
            "password_hash": "not-used",
            "role": "student",
        }

        response = self.client.post(
            "/api/register",
            json={
                "name": "Test Student",
                "email": "student@example.com",
                "password": "test-password",
                "role": "student",
            },
        )

        self.assertEqual(response.status_code, 409)

    def test_public_registration_cannot_create_privileged_accounts(self):
        for role in ("cr", "professor", "admin"):
            with self.subTest(role=role):
                response = self.client.post(
                    "/api/register",
                    json={
                        "name": "Test User",
                        "email": f"{role}@example.com",
                        "password": "test-password",
                        "role": role,
                    },
                )
                self.assertEqual(response.status_code, 400)

    def test_private_endpoints_reject_anonymous_requests(self):
        self.assertEqual(self.client.get("/api/complaints").status_code, 401)
        self.assertEqual(self.client.post("/api/complaints", json={}).status_code, 403)
        self.assertEqual(self.client.get("/api/faculty").status_code, 403)
        self.assertEqual(self.client.get("/api/timetable").status_code, 401)
        self.assertEqual(self.client.get("/api/classrooms/available").status_code, 401)

    def test_frontend_is_served_without_exposing_project_files(self):
        for path in ("/", "/login.html", "/js/config.js"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()

        source_response = self.client.get("/backend/app.py")
        self.assertEqual(source_response.status_code, 404)
        source_response.close()

    def test_login_creates_session_and_me_returns_profile(self):
        registered = self.client.post(
            "/api/register",
            json={
                "name": "Test Student",
                "email": "student@example.com",
                "password": "test-password",
                "role": "student",
            },
        )
        self.assertEqual(registered.status_code, 201)

        response = self.client.post(
            "/api/login",
            json={
                "email": "STUDENT@example.com",
                "password": "test-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["role"], "student")
        profile = self.client.get("/api/me")
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.get_json()["user"]["name"], "Test Student")

    def test_login_rejects_incorrect_password(self):
        self.client.post(
            "/api/register",
            json={
                "name": "Test Student",
                "email": "student@example.com",
                "password": "test-password",
                "role": "student",
            },
        )

        response = self.client.post(
            "/api/login",
            json={
                "email": "student@example.com",
                "password": "incorrect-password",
            },
        )

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

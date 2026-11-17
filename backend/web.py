"""HTTP interface for the TEMPO frontend."""

import argparse
import json
import os
from pathlib import Path
from uuid import UUID

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge

from .auth import SESSION_DAYS, AccountExists, Accounts, NotSetUp
from .practice_controller import create_backend


BACKEND = Path(__file__).resolve().parent
SESSION_COOKIE = "tempo_session"


class Handler:
    def __init__(self, controller, accounts, secure_cookies):
        self.controller = controller
        self.accounts = accounts
        self.secure_cookies = secure_cookies

    def respond(self, status, result, cookie=None):
        response = jsonify(result)
        response.status_code = status
        response.headers["Cache-Control"] = "no-store"
        if cookie is not None:
            response.headers["Set-Cookie"] = cookie
        return response

    @staticmethod
    def session_token():
        return request.cookies.get(SESSION_COOKIE)

    def session_cookie(self, token):
        secure = "; Secure" if self.secure_cookies else ""
        if token is None:
            return f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0{secure}"
        return f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS * 86400}{secure}"

    @staticmethod
    def read_json():
        if request.mimetype != "application/json":
            raise ValueError("Expected a small JSON request")
        try:
            raw = request.get_data()
        except RequestEntityTooLarge as error:
            raise ValueError("Expected a small JSON request") from error
        if not raw:
            raise ValueError("Expected a small JSON request")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data

    def do_GET(self):
        if request.path == "/api/lines":
            return self.respond(200, self.controller.list_lines())
        if request.path == "/api/auth/me":
            return self.respond(200, {"user": self.accounts.user_for_token(self.session_token()),
                               "google_client_id": self.accounts.google_client_id})
        return self.respond(404, {"error": "Unknown API endpoint"})

    def do_POST(self):
        if request.path.startswith("/api/auth/"):
            return self.handle_auth()
        # path: (action, required fields, optional fields)
        routes = {
            "/api/catalog": (self.controller.learning_catalog, (), ()),
            "/api/learning": (self.controller.start_learning, ("line_id", "side"), ("resume_at",)),
            "/api/review": (self.controller.start_repeating, (), ()),
            "/api/review/side": (self.controller.choose_review_side, ("session_id", "side"), ()),
            "/api/review/line": (self.controller.start_review_line, ("line_id",), ()),
            "/api/review/abandon": (self.controller.abandon_review, ("session_id",), ()),
            "/api/move": (self.controller.submit_move, ("session_id", "move_index", "move_uci"), ("response_time_ms",)),
            "/api/repertoire": (self.controller.repertoire, (), ()),
        }
        if request.path not in routes:
            return self.respond(404, {"error": "Unknown API endpoint"})
        try:
            data = self.read_json()
            user = self.accounts.user_for_token(self.session_token())
            if user is not None:
                player_id = user["user_id"]          # a signed-in player always acts as their account
            else:
                if not isinstance(data.get("player_id"), str):
                    raise ValueError("Expected a player ID")
                player_id = UUID(data["player_id"]).hex
                if self.accounts.is_registered(player_id):
                    return self.respond(401, {"error": "Sign in to use this account"})
            action, fields, optional = routes[request.path]
            extra = {field: data[field] for field in optional if field in data}
            result = action(player_id, *(data[field] for field in fields), **extra)
        except (KeyError, TypeError, ValueError) as error:
            return self.respond(400, {"error": str(error)})
        except LookupError as error:
            return self.respond(404, {"error": str(error)})
        else:
            return self.respond(200, result)

    def handle_auth(self):
        try:
            data = self.read_json()
            if request.path == "/api/auth/logout":
                self.accounts.logout(self.session_token())
                return self.respond(200, {"user": None}, cookie=self.session_cookie(None))
            if request.path in ("/api/auth/profile", "/api/auth/password", "/api/auth/delete"):
                current = self.accounts.user_for_token(self.session_token())
                if current is None:
                    return self.respond(401, {"error": "Sign in to change your account"})
                user_id = current["user_id"]
                if request.path == "/api/auth/profile":
                    return self.respond(200, {"user": self.accounts.update_profile(user_id, data.get("name"), data.get("email"))})
                if request.path == "/api/auth/password":
                    return self.respond(200, {"user": self.accounts.change_password(
                        user_id, data.get("current_password"), data.get("new_password"))})
                self.accounts.delete_account(user_id, data.get("password"), data.get("confirm"))
                return self.respond(200, {"user": None}, cookie=self.session_cookie(None))
            if request.path == "/api/auth/register":
                user, token = self.accounts.register(
                    data.get("name"), data.get("email"), data.get("password"))
            elif request.path == "/api/auth/login":
                user, token = self.accounts.login(data.get("email"), data.get("password"))
            elif request.path == "/api/auth/google":
                user, token = self.accounts.google(data.get("credential"))
            else:
                return self.respond(404, {"error": "Unknown API endpoint"})
        except AccountExists as error:
            return self.respond(409, {"error": str(error)})
        except PermissionError as error:
            return self.respond(401, {"error": str(error)})
        except NotSetUp as error:
            return self.respond(503, {"error": str(error)})
        except (KeyError, TypeError, ValueError) as error:
            return self.respond(400, {"error": str(error)})
        else:
            return self.respond(200, {"user": user}, cookie=self.session_cookie(token))


def create_app(database, weights, google_client_id=None, *, secure_cookies=False):
    dist = BACKEND.parent / "frontend" / "dist"
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 4096
    controller = create_backend(database, weights_file=weights)
    accounts = Accounts(controller.store, google_client_id=google_client_id)
    handler = Handler(controller, accounts, secure_cookies)
    app.add_url_rule("/api/<path:endpoint>", "api_get", lambda endpoint: handler.do_GET(), methods=["GET"])
    app.add_url_rule("/api/<path:endpoint>", "api_post", lambda endpoint: handler.do_POST(), methods=["POST"])

    @app.get("/", defaults={"asset": "index.html"})
    @app.get("/<path:asset>")
    def frontend(asset):
        return send_from_directory(dist, asset)

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=BACKEND / "tempo_demo.sqlite")
    parser.add_argument("--weights", type=Path, default=BACKEND / "fitted_global.csv")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--google-client-id", default=os.environ.get("TEMPO_GOOGLE_CLIENT_ID"),
                        help="OAuth client ID for Sign in with Google (or set TEMPO_GOOGLE_CLIENT_ID)")
    args = parser.parse_args()
    for path in (args.database, args.weights):
        if not path.is_file():
            parser.error(f"Required demo file is missing: {path}")
    app = create_app(args.database, args.weights, args.google_client_id)
    app.run(host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()

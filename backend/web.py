"""Local HTTP interface for the TEMPO frontend."""

import argparse
import json
import os
from functools import partial
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID

from .auth import SESSION_DAYS, AccountExists, Accounts, NotSetUp
from .practice_controller import create_backend


BACKEND = Path(__file__).resolve().parent
SESSION_COOKIE = "tempo_session"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, controller, accounts, **kwargs):
        self.controller = controller
        self.accounts = accounts
        super().__init__(*args, directory=BACKEND.parent / "frontend" / "dist", **kwargs)

    def respond(self, status, result, cookie=None):
        body = json.dumps(result).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def session_token(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        return cookie[SESSION_COOKIE].value if SESSION_COOKIE in cookie else None

    @staticmethod
    def session_cookie(token):
        if token is None:
            return f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
        return f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS * 86400}"

    def read_json(self):
        size = int(self.headers.get("Content-Length", "0"))
        if self.headers.get_content_type() != "application/json" or not 0 < size <= 4096:
            raise ValueError("Expected a small JSON request")
        data = json.loads(self.rfile.read(size))
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data

    def do_GET(self):
        if self.path == "/api/lines":
            self.respond(200, self.controller.list_lines())
        elif self.path == "/api/auth/me":
            self.respond(200, {"user": self.accounts.user_for_token(self.session_token()),
                               "google_client_id": self.accounts.google_client_id})
        elif self.path.startswith("/api/"):
            self.respond(404, {"error": "Unknown API endpoint"})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/auth/"):
            self.handle_auth()
            return
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
        if self.path not in routes:
            self.respond(404, {"error": "Unknown API endpoint"})
            return
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
                    self.respond(401, {"error": "Sign in to use this account"})
                    return
            action, fields, optional = routes[self.path]
            extra = {field: data[field] for field in optional if field in data}
            result = action(player_id, *(data[field] for field in fields), **extra)
        except (KeyError, TypeError, ValueError) as error:
            self.respond(400, {"error": str(error)})
        except LookupError as error:
            self.respond(404, {"error": str(error)})
        else:
            self.respond(200, result)

    def handle_auth(self):
        try:
            data = self.read_json()
            if self.path == "/api/auth/logout":
                self.accounts.logout(self.session_token())
                self.respond(200, {"user": None}, cookie=self.session_cookie(None))
                return
            if self.path in ("/api/auth/profile", "/api/auth/password", "/api/auth/delete"):
                current = self.accounts.user_for_token(self.session_token())
                if current is None:
                    self.respond(401, {"error": "Sign in to change your account"})
                    return
                user_id = current["user_id"]
                if self.path == "/api/auth/profile":
                    self.respond(200, {"user": self.accounts.update_profile(user_id, data.get("name"), data.get("email"))})
                elif self.path == "/api/auth/password":
                    self.respond(200, {"user": self.accounts.change_password(
                        user_id, data.get("current_password"), data.get("new_password"))})
                else:
                    self.accounts.delete_account(user_id, data.get("password"), data.get("confirm"))
                    self.respond(200, {"user": None}, cookie=self.session_cookie(None))
                return
            if self.path == "/api/auth/register":
                user, token = self.accounts.register(
                    data.get("name"), data.get("email"), data.get("password"))
            elif self.path == "/api/auth/login":
                user, token = self.accounts.login(data.get("email"), data.get("password"))
            elif self.path == "/api/auth/google":
                user, token = self.accounts.google(data.get("credential"))
            else:
                self.respond(404, {"error": "Unknown API endpoint"})
                return
        except AccountExists as error:
            self.respond(409, {"error": str(error)})
        except PermissionError as error:
            self.respond(401, {"error": str(error)})
        except NotSetUp as error:
            self.respond(503, {"error": str(error)})
        except (KeyError, TypeError, ValueError) as error:
            self.respond(400, {"error": str(error)})
        else:
            self.respond(200, {"user": user}, cookie=self.session_cookie(token))


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
    controller = create_backend(args.database, weights_file=args.weights)
    accounts = Accounts(controller.store, google_client_id=args.google_client_id)
    with ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, controller=controller, accounts=accounts)) as server:
        print(f"TEMPO listening at http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()

"""Local HTTP interface for the TEMPO frontend."""

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID

from .practice_controller import create_backend


BACKEND = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, controller, **kwargs):
        self.controller = controller
        super().__init__(*args, directory=BACKEND.parent / "frontend" / "dist", **kwargs)

    def respond(self, status, result):
        body = json.dumps(result).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/lines":
            self.respond(200, self.controller.list_lines())
        elif self.path.startswith("/api/"):
            self.respond(404, {"error": "Unknown API endpoint"})
        else:
            super().do_GET()

    def do_POST(self):
        # path: (action, required fields, optional fields)
        routes = {
            "/api/catalog": (self.controller.learning_catalog, (), ()),
            "/api/learning": (self.controller.start_learning, ("line_id", "side"), ("resume_at",)),
            "/api/review": (self.controller.start_repeating, (), ()),
            "/api/review/side": (self.controller.choose_review_side, ("session_id", "side"), ()),
            "/api/review/line": (self.controller.start_review_line, ("line_id",), ()),
            "/api/review/abandon": (self.controller.abandon_review, ("session_id",), ()),
            "/api/move": (self.controller.submit_move, ("session_id", "move_index", "move_uci"), ()),
            "/api/repertoire": (self.controller.repertoire, (), ()),
        }
        if self.path not in routes:
            self.respond(404, {"error": "Unknown API endpoint"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if self.headers.get_content_type() != "application/json" or not 0 < size <= 4096:
                raise ValueError("Expected a small JSON request")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict) or not isinstance(data.get("player_id"), str):
                raise ValueError("Expected a player ID")
            player_id = UUID(data["player_id"]).hex
            action, fields, optional = routes[self.path]
            extra = {field: data[field] for field in optional if field in data}
            result = action(player_id, *(data[field] for field in fields), **extra)
        except (KeyError, TypeError, ValueError) as error:
            self.respond(400, {"error": str(error)})
        except LookupError as error:
            self.respond(404, {"error": str(error)})
        else:
            self.respond(200, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=BACKEND / "tempo_demo.sqlite")
    parser.add_argument("--weights", type=Path, default=BACKEND / "fitted_global.csv")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    for path in (args.database, args.weights):
        if not path.is_file():
            parser.error(f"Required demo file is missing: {path}")
    controller = create_backend(args.database, weights_file=args.weights)
    with ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, controller=controller)) as server:
        print(f"TEMPO listening at http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()

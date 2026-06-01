import argparse
import json
import mimetypes
import posixpath
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, unquote, urlparse


APP_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = APP_ROOT / "frontend"

try:
    from .services import DataRepository, ModelService, assistant_answer
except ImportError:
    from services import DataRepository, ModelService, assistant_answer  # type: ignore


MODEL_SERVICE = ModelService()
REPOSITORY = DataRepository(MODEL_SERVICE)


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return str(value)


class MedicalAppHandler(BaseHTTPRequestHandler):
    server_version = "NMRMedicalApp/1.0"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/api/health":
                self.send_json({"status": "ok", "app": "nmr_metabolomics_medical_app"})
            elif path == "/api/summary":
                self.send_json(REPOSITORY.summary())
            elif path == "/api/performance":
                self.send_json(REPOSITORY.performance())
            elif path == "/api/features":
                self.send_json(MODEL_SERVICE.metadata())
            elif path == "/api/trajectories":
                self.send_json(REPOSITORY.trajectories())
            elif path == "/api/samples":
                q = query.get("q", [""])[0]
                state = query.get("state", [""])[0]
                limit = int(query.get("limit", ["120"])[0])
                self.send_json({"samples": REPOSITORY.list_samples(q=q, state=state, limit=limit)})
            elif path.startswith("/api/sample/"):
                sample_name = unquote(path.split("/api/sample/", 1)[1])
                sample = REPOSITORY.get_sample(sample_name)
                if sample is None:
                    self.send_error_json(HTTPStatus.NOT_FOUND, f"Sample not found: {sample_name}")
                else:
                    self.send_json(sample)
            else:
                self.serve_static(path)
        except Exception as exc:
            traceback.print_exc()
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()
            if parsed.path == "/api/predict":
                metabolites = payload.get("metabolites") or {}
                value_type = payload.get("value_type", "log1p")
                prediction = MODEL_SERVICE.predict(metabolites, value_type=value_type)
                prediction_id = REPOSITORY.save_custom_prediction("medical_app", payload, prediction)
                self.send_json({"prediction_id": prediction_id, "prediction": prediction})
            elif parsed.path == "/api/assistant":
                question = str(payload.get("question", "")).strip()
                if not question:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, "question is required")
                    return
                sample = None
                sample_name = payload.get("sample_name")
                if sample_name:
                    sample = REPOSITORY.get_sample(str(sample_name))
                self.send_json(assistant_answer(question, sample, REPOSITORY.summary()))
            else:
                self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown endpoint")
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:
            traceback.print_exc()
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"error": message}, status=status)

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        safe_path = posixpath.normpath(unquote(path)).lstrip("/")
        file_path = (FRONTEND_DIR / safe_path).resolve()
        frontend_root = FRONTEND_DIR.resolve()
        if not str(file_path).startswith(str(frontend_root)) or not file_path.is_file():
            self.send_error_json(HTTPStatus.NOT_FOUND, "File not found")
            return

        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        if file_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif file_path.suffix in (".html", ".css"):
            content_type += "; charset=utf-8"

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the connected NMR medical dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8766, type=int)
    parser.add_argument("--no-rebuild-db", action="store_true")
    args = parser.parse_args()

    REPOSITORY.initialize(force_rebuild=not args.no_rebuild_db)
    server = ThreadingHTTPServer((args.host, args.port), MedicalAppHandler)
    print(f"NMR Metabolomics Medical App running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

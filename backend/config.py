import os

from dotenv import load_dotenv

from .paths import DEFAULT_DB_PATH, DOTENV_PATH, REPO_ROOT, SCHEMA_PATH


PROJECT_ROOT = REPO_ROOT

# Load .env from the repository root (safe if missing).
load_dotenv(dotenv_path=DOTENV_PATH)

DB_PATH = os.environ.get("MIDI_MAPPER_DB_PATH") or str(DEFAULT_DB_PATH)
WS_POLL_INTERVAL = float(os.environ.get("MIDI_MAPPER_WS_POLL_INTERVAL", "0.01"))
MAX_NOTE = int(os.environ.get("MIDI_MAPPER_MAX_NOTE", "127"))

CORS_ORIGINS = os.environ.get("MIDI_MAPPER_CORS_ORIGINS", "*")
ALLOW_ORIGINS = ["*"] if CORS_ORIGINS.strip() == "*" else [s.strip() for s in CORS_ORIGINS.split(",") if s.strip()]

EXEC_PATH_ENV = os.environ.get("MIDI_MAPPER_EXEC_PATH", "$PATH")
EXEC_USE_SHELL = os.environ.get("MIDI_MAPPER_EXEC_USE_SHELL", "false").lower() in ("true", "1", "yes")

if EXEC_PATH_ENV == "$PATH" or not EXEC_PATH_ENV:
    EXEC_PATH = os.environ.get("PATH", "")
else:
    EXEC_PATH = EXEC_PATH_ENV.replace("$PATH", os.environ.get("PATH", ""))

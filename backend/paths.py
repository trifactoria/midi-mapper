from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    """Find the repository root that contains schema.sql."""
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "schema.sql").is_file():
            return candidate

    return Path(__file__).resolve().parents[1]


REPO_ROOT = find_repo_root()
SCHEMA_PATH = REPO_ROOT / "schema.sql"
DOTENV_PATH = REPO_ROOT / ".env"
DEFAULT_DB_PATH = REPO_ROOT / "midi_map.db"

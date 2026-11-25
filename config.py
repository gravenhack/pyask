import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def get_database_settings():
    required_settings = ("PYASK_DB_USER", "PYASK_DB_PASSWORD")
    missing_settings = [
        setting for setting in required_settings if not os.environ.get(setting)
    ]
    if missing_settings:
        missing = ", ".join(missing_settings)
        raise RuntimeError(f"Missing required database settings: {missing}")

    try:
        port = int(os.environ.get("PYASK_DB_PORT", "3306"))
    except ValueError as exc:
        raise ValueError("PYASK_DB_PORT must be an integer.") from exc

    if not 1 <= port <= 65535:
        raise ValueError("PYASK_DB_PORT must be between 1 and 65535.")

    return {
        "host": os.environ.get("PYASK_DB_HOST", "127.0.0.1"),
        "port": port,
        "user": os.environ["PYASK_DB_USER"],
        "password": os.environ["PYASK_DB_PASSWORD"],
        "database": os.environ.get("PYASK_DB_NAME", "pyask_db"),
        "charset": "utf8mb4",
        "use_unicode": True,
    }

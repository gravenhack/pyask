import os

from dotenv import load_dotenv

load_dotenv()

def get_database_settings():
    user = os.getenv("PYASK_DB_USER")
    password = os.getenv("PYASK_DB_PASSWORD")
    if not user or not password:
        raise ValueError(
            "PYASK_DB_USER and PYASK_DB_PASSWORD are required."
        )
    try:
        port = int(os.getenv("PYASK_DB_PORT", "3306"))
    except ValueError as exc:
        raise ValueError("PYASK_DB_PORT must be an integer.") from exc

    if not 1 <= port <= 65535:
        raise ValueError("PYASK_DB_PORT must be between 1 and 65535.")

    return {
        "host": os.getenv("PYASK_DB_HOST", "127.0.0.1"),
        "port": port,
        "user": user,
        "password": password,
        "database": os.getenv("PYASK_DB_NAME", "pyask_db"),
        "charset": "utf8mb4",
        "use_unicode": True,
    }

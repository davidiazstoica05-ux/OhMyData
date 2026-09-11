from pathlib import Path
import sqlite3


def get_db_path():
    """Returns the path to the SQLite database file."""
    return Path(__file__).resolve().parent.parent.parent / "db" / "MyData.db"

def get_connection():
    """Returns a connection to the local SQLite database."""
    return sqlite3.connect(get_db_path())


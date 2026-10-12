from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


@contextmanager
def database_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        yield connection
        connection.commit()
    except sqlite3.Error as error:
        try:
            connection.rollback()
        except Exception:
            pass
        raise DatabaseError("Database operation failed") from error
    except BaseException:
        try:
            connection.rollback()
        except Exception:
            pass
        raise
    finally:
        connection.close()


class DatabaseError(RuntimeError):
    """Raised when a SQLite operation cannot complete safely."""

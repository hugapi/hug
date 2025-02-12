import sqlite3
import json
import logging

class SQLStore:
    def __init__(self, db_path=':memory:', logger=None):
        self._logger = logger if logger is not None else logging.getLogger("hug")
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._cursor = self._conn.cursor()
        self._cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (
                                id TEXT PRIMARY KEY,
                                data TEXT
                              )''')
        self._conn.commit()

    def get(self, key):
        try:
            self._cursor.execute("SELECT data FROM sessions WHERE id = ?", (key,))
            row = self._cursor.fetchone()
            return json.loads(row[0]) if row else {}
        except Exception as e:
            self._logger.exception("SQL Exception: {}".format(str(e)))
            return {}

    def set(self, key, data):
        try:
            self._cursor.execute("REPLACE INTO sessions (id, data) VALUES (?, ?)", (key, json.dumps(data)))  # Serialize JSON
            self._conn.commit()
        except Exception as e:
            self._logger.exception("SQL Exception: {}".format(str(e)))
            raise

    def exists(self, key):
        try:
            self._cursor.execute("SELECT 1 FROM sessions WHERE id = ?", (key,))
            return self._cursor.fetchone() is not None
        except Exception as e:
            self._logger.exception("SQL Exception: {}".format(str(e)))
            raise

    def delete(self, key):
        try:
            self._cursor.execute("DELETE FROM sessions WHERE id = ?", (key,))
            self._conn.commit()
        except Exception as e:
            self._logger.exception("SQL Exception: {}".format(str(e)))
            raise
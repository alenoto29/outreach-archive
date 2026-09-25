import os
import sqlite3
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

import db
from init_db import initialize


class LocalDatabaseTests(unittest.TestCase):
    def test_isolated_databases_and_backup_restore(self):
        previous_db_path = os.environ.get("DB_PATH")
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.sqlite"
            second = Path(directory) / "second.sqlite"
            backup = Path(directory) / "backup.sqlite"
            initialize(first)
            initialize(second)

            os.environ["DB_PATH"] = str(first)
            db.execute("INSERT INTO publishers (name, domain, market) VALUES (?,?,?)",
                       ("Fictional Utility One", "one.example.test", "IT"))
            self.assertEqual(db.query("SELECT COUNT(*) AS n FROM publishers", one=True)["n"], 1)

            def insert_publisher(index):
                return db.execute(
                    "INSERT INTO publishers (name, domain, market) VALUES (?,?,?)",
                    (f"Fictional Concurrent {index}", f"concurrent-{index}.example.test", "IT"),
                )

            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(insert_publisher, range(6)))
            self.assertEqual(db.query("SELECT COUNT(*) AS n FROM publishers", one=True)["n"], 7)

            os.environ["DB_PATH"] = str(second)
            self.assertEqual(db.query("SELECT COUNT(*) AS n FROM publishers", one=True)["n"], 0)

            source = sqlite3.connect(second)
            destination = sqlite3.connect(backup)
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
            restored = sqlite3.connect(backup)
            try:
                restored.execute("INSERT INTO publishers (name, domain, market) VALUES (?,?,?)",
                                 ("Fictional Utility Two", "two.example.test", "IT"))
                restored.commit()
                self.assertEqual(restored.execute("SELECT COUNT(*) FROM publishers").fetchone()[0], 1)
                self.assertEqual(restored.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            finally:
                restored.close()
        if previous_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = previous_db_path


if __name__ == "__main__":
    unittest.main()

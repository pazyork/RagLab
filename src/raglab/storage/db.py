import sqlite3
import os
from typing import List, Tuple, Optional, Dict, Union


class Database:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            self.path = os.path.expanduser("~/.raglab.db")
        else:
            self.path = path

        self.conn = sqlite3.connect(self.path)
        self._enable_foreign_keys()
        self._create_tables()

    def _enable_foreign_keys(self):
        """Enable foreign key constraints."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        self.conn.commit()

    def _create_tables(self):
        """Create all required tables if they don't exist."""
        cursor = self.conn.cursor()

        # providers table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            api_key TEXT NOT NULL,
            base_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # models table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            model_type TEXT DEFAULT 'embedding',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (provider_id) REFERENCES providers(id),
            UNIQUE(provider_id, model_name)
        )
        ''')

        # test_cases table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # case_chunks table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS case_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE
        )
        ''')

        # eval_runs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS eval_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            model TEXT NOT NULL,
            metric TEXT DEFAULT 'cosine',
            algorithm TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES test_cases(id)
        )
        ''')

        # eval_scores table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS eval_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            score REAL NOT NULL,
            rank INTEGER NOT NULL,
            FOREIGN KEY (run_id) REFERENCES eval_runs(id) ON DELETE CASCADE
        )
        ''')

        # config table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        ''')

        self.conn.commit()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    # Providers methods
    def add_provider(self, name: str, api_key: str, base_url: Optional[str] = None) -> int:
        """Add a new provider and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO providers (name, api_key, base_url) VALUES (?, ?, ?)",
            (name, api_key, base_url)
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_providers(self) -> List[Tuple]:
        """List all providers."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM providers ORDER BY created_at DESC")
        return cursor.fetchall()

    def get_provider(self, name: str) -> Optional[Tuple]:
        """Get a provider by name, return None if not found."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM providers WHERE name = ?", (name,))
        return cursor.fetchone()

    def remove_provider(self, name: str):
        """Remove a provider by name."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM providers WHERE name = ?", (name,))
        self.conn.commit()

    # Models methods
    def add_model(self, provider_id: int, model_name: str, model_type: str = 'embedding') -> int:
        """Add a new model and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO models (provider_id, model_name, model_type) VALUES (?, ?, ?)",
            (provider_id, model_name, model_type)
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_models(self, provider_name: Optional[str] = None) -> List[Tuple]:
        """List all models, optionally filtered by provider name."""
        cursor = self.conn.cursor()
        if provider_name:
            cursor.execute('''
                SELECT m.* FROM models m
                JOIN providers p ON m.provider_id = p.id
                WHERE p.name = ?
                ORDER BY m.created_at DESC
            ''', (provider_name,))
        else:
            cursor.execute("SELECT * FROM models ORDER BY created_at DESC")
        return cursor.fetchall()

    # Test Cases methods
    def add_case(self, name: str, description: Optional[str] = None) -> int:
        """Add a new test case and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO test_cases (name, description) VALUES (?, ?)",
            (name, description)
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_cases(self) -> List[Tuple]:
        """List all test cases."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM test_cases ORDER BY created_at DESC")
        return cursor.fetchall()

    def get_case(self, case_id: int) -> Optional[Tuple]:
        """Get a test case by ID, return None if not found."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM test_cases WHERE id = ?", (case_id,))
        return cursor.fetchone()

    def remove_case(self, case_id: int):
        """Remove a test case by ID (cascades to chunks)."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
        self.conn.commit()

    # Chunks methods
    def add_chunks(self, case_id: int, chunks: List[str]):
        """Add multiple chunks for a test case."""
        cursor = self.conn.cursor()
        for index, content in enumerate(chunks):
            cursor.execute(
                "INSERT INTO case_chunks (case_id, chunk_index, content) VALUES (?, ?, ?)",
                (case_id, index, content)
            )
        self.conn.commit()

    def get_chunks(self, case_id: int) -> List[Tuple]:
        """Get all chunks for a test case, ordered by chunk_index."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM case_chunks WHERE case_id = ? ORDER BY chunk_index ASC",
            (case_id,)
        )
        return cursor.fetchall()

    # Eval Runs methods
    def add_run(self, case_id: int, name: str, model: str, metric: str = 'cosine', algorithm: Optional[str] = None) -> int:
        """Add a new evaluation run and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO eval_runs (case_id, name, model, metric, algorithm) VALUES (?, ?, ?, ?, ?)",
            (case_id, name, model, metric, algorithm)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_run_status(self, run_id: int, status: str):
        """Update the status of an evaluation run."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE eval_runs SET status = ? WHERE id = ?",
            (status, run_id)
        )
        self.conn.commit()

    def list_runs(self, case_id: Optional[int] = None) -> List[Tuple]:
        """List all evaluation runs, optionally filtered by case ID."""
        cursor = self.conn.cursor()
        if case_id:
            cursor.execute(
                "SELECT * FROM eval_runs WHERE case_id = ? ORDER BY created_at DESC",
                (case_id,)
            )
        else:
            cursor.execute("SELECT * FROM eval_runs ORDER BY created_at DESC")
        return cursor.fetchall()

    def add_scores(self, run_id: int, scores: List[Tuple[int, float, int]]):
        """Add multiple scores for an evaluation run."""
        cursor = self.conn.cursor()
        for chunk_index, score, rank in scores:
            cursor.execute(
                "INSERT INTO eval_scores (run_id, chunk_index, score, rank) VALUES (?, ?, ?, ?)",
                (run_id, chunk_index, score, rank)
            )
        self.conn.commit()

    def get_scores(self, run_id: int) -> List[Tuple]:
        """Get all scores for an evaluation run, ordered by chunk_index."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM eval_scores WHERE run_id = ? ORDER BY chunk_index ASC",
            (run_id,)
        )
        return cursor.fetchall()

    # Config methods
    def set_config(self, key: str, value: Union[int, float, str]):
        """Set a config value (automatically converted to string)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        self.conn.commit()

    def get_config(self, key: str) -> Optional[Union[int, float, str]]:
        """Get a config value with automatic type inference."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        result = cursor.fetchone()
        if result is None:
            return None

        value = result[0]

        # Try to convert to int first
        try:
            return int(value)
        except ValueError:
            pass

        # Then try float
        try:
            return float(value)
        except ValueError:
            pass

        # Otherwise return as string
        return value

    def get_all_config(self) -> Dict[str, Union[int, float, str]]:
        """Get all config values as a dictionary with type inference."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM config")
        rows = cursor.fetchall()

        config = {}
        for key, value in rows:
            # Apply type inference
            try:
                config[key] = int(value)
                continue
            except ValueError:
                pass

            try:
                config[key] = float(value)
                continue
            except ValueError:
                pass

            config[key] = value

        return config

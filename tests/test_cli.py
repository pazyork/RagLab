"""Tests for raglab CLI commands using typer.testing.CliRunner."""

import json
import os
import tempfile

import pytest
from typer.testing import CliRunner

from raglab.cli import app, get_db
from raglab.storage.db import Database

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch, tmp_path):
    """Redirect the DB singleton to a temp file for every test."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)

    # Reset the module-level singleton so get_db() returns our temp db
    import raglab.cli as cli_mod

    monkeypatch.setattr(cli_mod, "_db", db)
    monkeypatch.setattr(cli_mod, "_embedder", None)

    yield db

    db.close()


# ---------------------------------------------------------------------------
# Provider commands
# ---------------------------------------------------------------------------


class TestProvider:
    def test_add_list_remove(self):
        # add
        result = runner.invoke(app, ["provider", "add", "openai", "--api-key", "sk-123"])
        assert result.exit_code == 0
        assert "openai" in result.output

        # list
        result = runner.invoke(app, ["provider", "list"])
        assert result.exit_code == 0
        assert "openai" in result.output

        # remove with --force
        result = runner.invoke(app, ["provider", "remove", "openai", "--force"])
        assert result.exit_code == 0
        assert "removed" in result.output

        # verify gone
        result = runner.invoke(app, ["provider", "list"])
        assert "No providers" in result.output

    def test_add_with_base_url(self):
        result = runner.invoke(app, [
            "provider", "add", "ollama", "--api-key", "dummy", "--base-url", "http://localhost:11434"
        ])
        assert result.exit_code == 0

        result = runner.invoke(app, ["provider", "list"])
        assert "ollama" in result.output
        assert "localhost" in result.output

    def test_remove_nonexistent(self):
        result = runner.invoke(app, ["provider", "remove", "ghost", "--force"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_remove_interactive_abort(self):
        runner.invoke(app, ["provider", "add", "temp", "--api-key", "k"])
        result = runner.invoke(app, ["provider", "remove", "temp"], input="n\n")
        assert result.exit_code == 1  # Aborted


# ---------------------------------------------------------------------------
# Config commands
# ---------------------------------------------------------------------------


class TestConfig:
    def test_set_show_roundtrip(self):
        # set
        result = runner.invoke(app, ["config", "set", "chunk_size", "512"])
        assert result.exit_code == 0
        assert "chunk_size" in result.output

        # show
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "chunk_size" in result.output
        assert "512" in result.output

    def test_show_empty(self):
        result = runner.invoke(app, ["config", "show"])
        assert "No configuration" in result.output

    def test_reset(self):
        runner.invoke(app, ["config", "set", "k", "v"])
        result = runner.invoke(app, ["config", "reset", "--force"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["config", "show"])
        assert "No configuration" in result.output

    def test_reset_interactive_abort(self):
        runner.invoke(app, ["config", "set", "k", "v"])
        result = runner.invoke(app, ["config", "reset"], input="n\n")
        assert result.exit_code == 1  # Aborted


# ---------------------------------------------------------------------------
# Model commands
# ---------------------------------------------------------------------------


class TestModel:
    def test_list_empty(self):
        result = runner.invoke(app, ["model", "list"])
        assert "No models" in result.output

    def test_list_with_provider_filter(self, _isolate_db):
        db = _isolate_db
        pid = db.add_provider("openai", "sk-123")
        db.add_model(pid, "text-embedding-ada-002")

        result = runner.invoke(app, ["model", "list", "--provider", "openai"])
        assert result.exit_code == 0
        assert "text-embedding-ada-002" in result.output


# ---------------------------------------------------------------------------
# Split command
# ---------------------------------------------------------------------------


class TestSplit:
    def test_split_recursive(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Hello world.\n\nThis is paragraph two.\n\nAnd paragraph three.", encoding="utf-8")

        result = runner.invoke(app, ["split", str(f)])
        assert result.exit_code == 0
        assert "Chunk" in result.output or "index" in result.output

    def test_split_char_strategy(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("A" * 200, encoding="utf-8")

        result = runner.invoke(app, ["split", str(f), "--strategy", "char", "--chunk-size", "100", "--overlap", "10"])
        assert result.exit_code == 0

    def test_split_to_file(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Some text here.", encoding="utf-8")
        out = tmp_path / "out.txt"

        result = runner.invoke(app, ["split", str(f), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_split_unknown_strategy(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("text", encoding="utf-8")

        result = runner.invoke(app, ["split", str(f), "--strategy", "bogus"])
        assert result.exit_code == 1
        assert "Unknown strategy" in result.output


# ---------------------------------------------------------------------------
# Serve command
# ---------------------------------------------------------------------------


class TestServe:
    def test_serve_placeholder(self):
        result = runner.invoke(app, ["serve"])
        assert result.exit_code == 0
        assert "coming soon" in result.output.lower()

    def test_serve_help(self):
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output


# ---------------------------------------------------------------------------
# Case commands
# ---------------------------------------------------------------------------


class TestCase:
    def test_add_and_list(self, tmp_path):
        f = tmp_path / "case.txt"
        f.write_text("Chunk one.\n\nChunk two.\n\nChunk three.", encoding="utf-8")

        result = runner.invoke(app, ["case", "add", "mycase", str(f), "--description", "A test case"])
        assert result.exit_code == 0
        assert "mycase" in result.output
        assert "chunks" in result.output

        result = runner.invoke(app, ["case", "list"])
        assert result.exit_code == 0
        assert "mycase" in result.output

    def test_remove(self, tmp_path):
        f = tmp_path / "case.txt"
        f.write_text("Hello", encoding="utf-8")

        runner.invoke(app, ["case", "add", "delme", str(f)])
        result = runner.invoke(app, ["case", "remove", "delme", "--force"])
        assert result.exit_code == 0
        assert "removed" in result.output

    def test_remove_nonexistent(self):
        result = runner.invoke(app, ["case", "remove", "ghost", "--force"])
        assert result.exit_code == 1

    def test_add_nonexistent_file(self):
        result = runner.invoke(app, ["case", "add", "x", "/no/such/file.txt"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Score / Compare / Matrix — smoke tests (need no live API)
# ---------------------------------------------------------------------------


class TestScoreSmoke:
    def test_score_mutual_exclusion(self, tmp_path):
        """Both --model and --algorithm provided should error."""
        f = tmp_path / "t.txt"
        f.write_text("hello world", encoding="utf-8")

        result = runner.invoke(app, ["score", "q", str(f), "--model", "m", "--algorithm", "bm25"])
        # Should fail because both options are given
        assert result.exit_code == 1

    def test_score_no_provider(self, tmp_path):
        """--model without any provider configured should error."""
        f = tmp_path / "t.txt"
        f.write_text("hello world", encoding="utf-8")

        result = runner.invoke(app, ["score", "q", str(f), "--model", "m"])
        assert result.exit_code == 1
        assert "No providers" in result.output

    def test_score_sparse(self, tmp_path):
        """Sparse scoring should work without any provider."""
        f = tmp_path / "t.txt"
        f.write_text("Hello world. This is a test. Another chunk here.", encoding="utf-8")

        result = runner.invoke(app, ["score", "hello", str(f), "--algorithm", "bm25", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0


class TestCompareSmoke:
    def test_compare_no_provider(self, tmp_path):
        f = tmp_path / "t.txt"
        f.write_text("hello world", encoding="utf-8")

        result = runner.invoke(app, ["compare", "q", str(f), "--models", "m1,m2"])
        assert result.exit_code == 1


class TestMatrixSmoke:
    def test_matrix_no_provider(self, tmp_path):
        f = tmp_path / "t.txt"
        f.write_text("hello world", encoding="utf-8")

        result = runner.invoke(app, ["matrix", str(f), "--model", "m"])
        assert result.exit_code == 1
        assert "No providers" in result.output


# ---------------------------------------------------------------------------
# Output helper
# ---------------------------------------------------------------------------


class TestOutputHelper:
    def test_empty(self):
        from raglab.cli import _output_results

        assert "(no results)" in _output_results([], "table")

    def test_json_format(self):
        from raglab.cli import _output_results

        data = [{"a": 1, "b": "x"}]
        out = _output_results(data, "json")
        parsed = json.loads(out)
        assert parsed == data

    def test_csv_format(self):
        from raglab.cli import _output_results

        data = [{"a": 1, "b": "x"}]
        out = _output_results(data, "csv")
        lines = out.splitlines()
        assert "a,b" in lines[0]
        assert "1,x" in lines[1]

    def test_table_format(self):
        from raglab.cli import _output_results

        data = [{"name": "alice", "score": 0.9}]
        out = _output_results(data, "table")
        assert "name" in out
        assert "alice" in out

import os
import tempfile
import pytest
from raglab.storage.db import Database


class TestDatabase:
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing, cleaned up after use."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = Database(path)
        yield db
        db.close()
        os.unlink(path)

    def test_provider_crud(self, temp_db):
        """Test provider CRUD operations."""
        # Add provider
        provider_id = temp_db.add_provider("openai", "sk-123", "https://api.openai.com/v1")
        assert provider_id == 1

        # List providers
        providers = temp_db.list_providers()
        assert len(providers) == 1
        assert providers[0][1] == "openai"
        assert providers[0][2] == "sk-123"
        assert providers[0][3] == "https://api.openai.com/v1"

        # Get provider
        provider = temp_db.get_provider("openai")
        assert provider is not None
        assert provider[0] == 1
        assert provider[1] == "openai"

        # Remove provider
        temp_db.remove_provider("openai")
        assert temp_db.get_provider("openai") is None
        assert len(temp_db.list_providers()) == 0

    def test_model_crud(self, temp_db):
        """Test model CRUD operations."""
        provider_id = temp_db.add_provider("openai", "sk-123")

        # Add model
        model_id = temp_db.add_model(provider_id, "text-embedding-ada-002", "embedding")
        assert model_id == 1

        # List models by provider name
        models = temp_db.list_models("openai")
        assert len(models) == 1
        assert models[0][2] == "text-embedding-ada-002"
        assert models[0][3] == "embedding"

        # List all models
        all_models = temp_db.list_models()
        assert len(all_models) == 1

        # Add another model
        model_id2 = temp_db.add_model(provider_id, "gpt-4", "chat")
        assert model_id2 == 2
        assert len(temp_db.list_models("openai")) == 2

    def test_test_case_crud(self, temp_db):
        """Test test case CRUD operations."""
        # Add case
        case_id = temp_db.add_case("test_case_1", "Test case description")
        assert case_id == 1

        # List cases
        cases = temp_db.list_cases()
        assert len(cases) == 1
        assert cases[0][1] == "test_case_1"
        assert cases[0][2] == "Test case description"

        # Get case
        case = temp_db.get_case(case_id)
        assert case is not None
        assert case[1] == "test_case_1"

        # Remove case
        temp_db.remove_case(case_id)
        assert temp_db.get_case(case_id) is None
        assert len(temp_db.list_cases()) == 0

    def test_case_chunks(self, temp_db):
        """Test case chunks operations."""
        case_id = temp_db.add_case("test_case")

        # Add chunks
        chunks = ["chunk 1", "chunk 2", "chunk 3"]
        temp_db.add_chunks(case_id, chunks)

        # Get chunks
        stored_chunks = temp_db.get_chunks(case_id)
        assert len(stored_chunks) == 3
        assert stored_chunks[0][2] == 0  # chunk_index
        assert stored_chunks[0][3] == "chunk 1"
        assert stored_chunks[1][2] == 1
        assert stored_chunks[1][3] == "chunk 2"
        assert stored_chunks[2][2] == 2
        assert stored_chunks[2][3] == "chunk 3"

    def test_delete_case_cascades_chunks(self, temp_db):
        """Test that deleting a case cascades to its chunks."""
        case_id = temp_db.add_case("test_case")
        temp_db.add_chunks(case_id, ["chunk1", "chunk2"])

        assert len(temp_db.get_chunks(case_id)) == 2

        temp_db.remove_case(case_id)
        assert len(temp_db.get_chunks(case_id)) == 0

    def test_eval_runs_and_scores(self, temp_db):
        """Test eval runs and scores operations."""
        case_id = temp_db.add_case("test_case")
        provider_id = temp_db.add_provider("openai", "sk-123")
        model_id = temp_db.add_model(provider_id, "text-embedding-ada-002")

        # Add run
        run_id = temp_db.add_run(case_id, "run1", "text-embedding-ada-002", "cosine", "bm25")
        assert run_id == 1

        # List runs
        runs = temp_db.list_runs(case_id)
        assert len(runs) == 1
        assert runs[0][2] == "run1"
        assert runs[0][3] == "text-embedding-ada-002"
        assert runs[0][4] == "cosine"
        assert runs[0][5] == "bm25"
        assert runs[0][6] == "pending"  # default status

        # Update run status
        temp_db.update_run_status(run_id, "completed")
        runs = temp_db.list_runs(case_id)
        assert runs[0][6] == "completed"

        # Add scores
        scores = [(0, 0.95, 1), (1, 0.85, 2), (2, 0.75, 3)]
        temp_db.add_scores(run_id, scores)

        # Get scores
        stored_scores = temp_db.get_scores(run_id)
        assert len(stored_scores) == 3
        assert stored_scores[0][2] == 0  # chunk_index
        assert stored_scores[0][3] == 0.95  # score
        assert stored_scores[0][4] == 1  # rank
        assert stored_scores[1][2] == 1
        assert stored_scores[1][3] == 0.85
        assert stored_scores[1][4] == 2
        assert stored_scores[2][2] == 2
        assert stored_scores[2][3] == 0.75
        assert stored_scores[2][4] == 3

    def test_config_operations(self, temp_db):
        """Test config operations with type inference."""
        # Set config values
        temp_db.set_config("int_value", "512")
        temp_db.set_config("float_value", "0.5")
        temp_db.set_config("str_value", "hello world")
        temp_db.set_config("bool_str", "true")

        # Get config with type inference
        assert temp_db.get_config("int_value") == 512
        assert isinstance(temp_db.get_config("int_value"), int)

        assert temp_db.get_config("float_value") == 0.5
        assert isinstance(temp_db.get_config("float_value"), float)

        assert temp_db.get_config("str_value") == "hello world"
        assert isinstance(temp_db.get_config("str_value"), str)

        assert temp_db.get_config("bool_str") == "true"  # stays as string, no bool inference

        # Get non-existent key
        assert temp_db.get_config("non_existent") is None

        # Get all config
        all_config = temp_db.get_all_config()
        assert all_config == {
            "int_value": 512,
            "float_value": 0.5,
            "str_value": "hello world",
            "bool_str": "true"
        }

    def test_default_db_path(self):
        """Test default database path is ~/.raglab.db."""
        db = Database(None)
        expected_path = os.path.expanduser("~/.raglab.db")
        assert db.path == expected_path
        db.close()
        # Clean up if it was created
        if os.path.exists(expected_path):
            os.unlink(expected_path)

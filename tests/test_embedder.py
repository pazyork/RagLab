import pytest
import numpy as np
from unittest.mock import Mock, patch
from raglab.core.embedder import Embedder


class TestEmbedder:
    def test_initial_state(self):
        """Test that initial state is empty with no provider or model configured"""
        embedder = Embedder()
        assert embedder.provider is None
        assert embedder.model is None
        assert embedder.providers == {}

    def test_embed_before_configure_raises_error(self):
        """Test that embed() raises ValueError when no provider is configured"""
        embedder = Embedder()
        with pytest.raises(ValueError, match="No provider configured"):
            embedder.embed("test text")

    def test_configure_sets_provider_and_model(self):
        """Test that configure() correctly sets current provider and model"""
        embedder = Embedder()
        embedder.configure(
            provider="openai",
            api_key="test-key",
            model="text-embedding-ada-002",
            base_url="https://api.openai.com/v1"
        )

        assert embedder.provider == "openai"
        assert embedder.model == "text-embedding-ada-002"
        assert "openai" in embedder.providers
        assert embedder.providers["openai"]["api_key"] == "test-key"
        assert embedder.providers["openai"]["base_url"] == "https://api.openai.com/v1"

    def test_configure_without_base_url(self):
        """Test that configure() works without base_url parameter"""
        embedder = Embedder()
        embedder.configure(
            provider="openai",
            api_key="test-key",
            model="text-embedding-ada-002"
        )

        assert embedder.provider == "openai"
        assert embedder.model == "text-embedding-ada-002"
        assert embedder.providers["openai"]["base_url"] is None

    def test_load_config_bulk_loads_providers(self):
        """Test that load_config() loads multiple providers at once"""
        embedder = Embedder()
        providers_config = {
            "openai": {
                "api_key": "openai-key",
                "base_url": "https://api.openai.com/v1"
            },
            "anthropic": {
                "api_key": "anthropic-key",
                "base_url": "https://api.anthropic.com"
            }
        }

        embedder.load_config(providers_config)

        assert len(embedder.providers) == 2
        assert "openai" in embedder.providers
        assert "anthropic" in embedder.providers
        assert embedder.providers["openai"]["api_key"] == "openai-key"
        assert embedder.providers["anthropic"]["base_url"] == "https://api.anthropic.com"

    def test_switch_provider_after_configure(self):
        """Test that configure() can switch between different providers"""
        embedder = Embedder()

        # Configure first provider
        embedder.configure(
            provider="openai",
            api_key="openai-key",
            model="text-embedding-ada-002"
        )

        # Configure second provider
        embedder.configure(
            provider="anthropic",
            api_key="anthropic-key",
            model="claude-3-sonnet-20240229"
        )

        assert embedder.provider == "anthropic"
        assert embedder.model == "claude-3-sonnet-20240229"
        assert "openai" in embedder.providers  # First provider should still be in config
        assert "anthropic" in embedder.providers

    @patch('raglab.core.embedder.litellm')
    def test_embed_single_text_returns_1d_array(self, mock_litellm):
        """Test that embed() with single text returns 1D numpy array"""
        # Mock the litellm response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3, 0.4])]
        mock_litellm.embedding.return_value = mock_response

        embedder = Embedder()
        embedder.configure(
            provider="openai",
            api_key="test-key",
            model="text-embedding-ada-002"
        )

        result = embedder.embed("test text")

        assert isinstance(result, np.ndarray)
        assert result.shape == (4,)
        np.testing.assert_allclose(result, [0.1, 0.2, 0.3, 0.4], rtol=1e-6)

        # Verify litellm was called correctly
        mock_litellm.embedding.assert_called_once_with(
            model="openai/text-embedding-ada-002",
            input="test text",
            api_key="test-key",
            base_url=None
        )

    @patch('raglab.core.embedder.litellm')
    def test_embed_batch_texts_returns_2d_array(self, mock_litellm):
        """Test that embed() with list of texts returns 2D numpy array"""
        # Mock the litellm response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6]),
            Mock(embedding=[0.7, 0.8, 0.9])
        ]
        mock_litellm.embedding.return_value = mock_response

        embedder = Embedder()
        embedder.configure(
            provider="openai",
            api_key="test-key",
            model="text-embedding-ada-002"
        )

        result = embedder.embed(["text1", "text2", "text3"])

        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 3)
        np.testing.assert_allclose(result[0], [0.1, 0.2, 0.3], rtol=1e-6)
        np.testing.assert_allclose(result[1], [0.4, 0.5, 0.6], rtol=1e-6)
        np.testing.assert_allclose(result[2], [0.7, 0.8, 0.9], rtol=1e-6)

        # Verify litellm was called correctly
        mock_litellm.embedding.assert_called_once_with(
            model="openai/text-embedding-ada-002",
            input=["text1", "text2", "text3"],
            api_key="test-key",
            base_url=None
        )

    @patch('raglab.core.embedder.litellm')
    def test_embed_batch_alias_works(self, mock_litellm):
        """Test that embed_batch() is an alias for embed() with list input"""
        # Mock the litellm response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6])
        ]
        mock_litellm.embedding.return_value = mock_response

        embedder = Embedder()
        embedder.configure(
            provider="openai",
            api_key="test-key",
            model="text-embedding-ada-002"
        )

        result = embedder.embed_batch(["text1", "text2"])

        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 3)

        # Verify litellm was called correctly
        mock_litellm.embedding.assert_called_once_with(
            model="openai/text-embedding-ada-002",
            input=["text1", "text2"],
            api_key="test-key",
            base_url=None
        )

    @patch('raglab.core.embedder.litellm')
    def test_embed_with_custom_base_url(self, mock_litellm):
        """Test that embed() uses the configured base_url"""
        # Mock the litellm response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_litellm.embedding.return_value = mock_response

        embedder = Embedder()
        embedder.configure(
            provider="openai",
            api_key="test-key",
            model="text-embedding-ada-002",
            base_url="https://custom.api.endpoint/v1"
        )

        embedder.embed("test text")

        # Verify litellm was called with custom base_url
        mock_litellm.embedding.assert_called_once_with(
            model="openai/text-embedding-ada-002",
            input="test text",
            api_key="test-key",
            base_url="https://custom.api.endpoint/v1"
        )

    @patch('raglab.core.embedder.litellm')
    def test_embed_api_failure_raises_runtime_error(self, mock_litellm):
        """Test that API failures are wrapped as RuntimeError"""
        # Make litellm raise an exception
        mock_litellm.embedding.side_effect = Exception("API rate limit exceeded")

        embedder = Embedder()
        embedder.configure(
            provider="openai",
            api_key="test-key",
            model="text-embedding-ada-002"
        )

        with pytest.raises(RuntimeError, match="Embedding API call failed: API rate limit exceeded"):
            embedder.embed("test text")

"""Unified embedding interface supporting multiple providers via litellm."""

import numpy as np
import litellm
from typing import Optional, Union, List


class Embedder:
    """Unified embedding interface that supports multiple LLM providers.

    This class encapsulates litellm's embedding functionality to provide a
    consistent interface across different embedding providers.
    """

    def __init__(self):
        """Initialize an empty Embedder instance."""
        self.providers: dict[str, dict] = {}
        self.model: Optional[str] = None
        self.provider: Optional[str] = None

    def configure(self, provider: str, api_key: str, model: str, base_url: Optional[str] = None) -> None:
        """Configure the current provider and model.

        Args:
            provider: Name of the embedding provider (e.g., "openai", "anthropic")
            api_key: API key for the provider
            model: Name of the embedding model to use
            base_url: Optional base URL for the provider's API
        """
        # Store provider configuration
        self.providers[provider] = {
            "api_key": api_key,
            "base_url": base_url
        }

        # Set current provider and model
        self.provider = provider
        self.model = model

    def load_config(self, providers: dict[str, dict]) -> None:
        """Bulk load provider configurations.

        Args:
            providers: Dictionary of provider configurations in the format:
                {
                    "provider_name": {
                        "api_key": "your-api-key",
                        "base_url": "https://api.example.com"  # optional
                    }
                }
        """
        for provider_name, config in providers.items():
            self.providers[provider_name] = {
                "api_key": config["api_key"],
                "base_url": config.get("base_url")
            }

    def embed(self, text: Union[str, List[str]]) -> np.ndarray:
        """Generate embeddings for single or multiple texts.

        Args:
            text: Single text string or list of text strings to embed

        Returns:
            numpy.ndarray: 1D array for single text, 2D array for multiple texts

        Raises:
            ValueError: If no provider or model is configured
            RuntimeError: If the API call fails
        """
        if not self.provider or not self.model:
            raise ValueError("No provider configured. Call configure() first.")

        if self.provider not in self.providers:
            raise ValueError(f"Provider '{self.provider}' not found in configuration.")

        provider_config = self.providers[self.provider]
        model_full_name = f"{self.provider}/{self.model}"

        try:
            response = litellm.embedding(
                model=model_full_name,
                input=text,
                api_key=provider_config["api_key"],
                base_url=provider_config["base_url"]
            )
        except Exception as e:
            raise RuntimeError(f"Embedding API call failed: {str(e)}") from e

        # Extract embeddings from response
        embeddings = [item.embedding for item in response.data]

        # Convert to numpy array
        if isinstance(text, str):
            return np.array(embeddings[0], dtype=np.float32)
        else:
            return np.array(embeddings, dtype=np.float32)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Alias for embed() that explicitly takes a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            numpy.ndarray: 2D array of embeddings
        """
        return self.embed(texts)

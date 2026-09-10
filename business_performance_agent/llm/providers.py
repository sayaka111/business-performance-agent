"""Explicit provider selection; no credentials are returned in metadata."""

PROVIDER_KEYS = {"gemini": "GEMINI_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}


def create_client(provider, model=None, **kwargs):
    if provider == "gemini":
        from .gemini_client import GeminiLLMClient

        return GeminiLLMClient(model, **kwargs)
    if provider == "deepseek":
        from .deepseek_client import DeepSeekLLMClient

        return DeepSeekLLMClient(model, **kwargs)
    raise ValueError("Unknown LLM provider")

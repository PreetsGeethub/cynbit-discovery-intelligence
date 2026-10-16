class ProviderRateLimitError(Exception):
    """The upstream LLM provider rejected a request due to rate/quota limits."""

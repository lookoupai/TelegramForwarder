from typing import Optional

from .openai_base_provider import OpenAIBaseProvider


class OpenAICompatibleProvider(OpenAIBaseProvider):
    def __init__(self, provider_key: str, default_model: str = "gpt-4o-mini", default_api_base: str = ""):
        super().__init__(
            env_prefix=provider_key.upper(),
            provider_key=provider_key,
            default_model=default_model,
            default_api_base=default_api_base,
        )


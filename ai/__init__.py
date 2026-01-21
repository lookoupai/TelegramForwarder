from .base import BaseAIProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepSeekProvider
from .qwen_provider import QwenProvider
from .grok_provider import GrokProvider
from .claude_provider import ClaudeProvider
from .openai_compatible_provider import OpenAICompatibleProvider
import os
import logging
from utils.settings import load_ai_models, load_ai_providers
from utils.constants import DEFAULT_AI_MODEL

# 获取日志记录器
logger = logging.getLogger(__name__)

_DEFAULT_PROVIDER_TYPE = {
    "openai": "openai_compatible",
    "deepseek": "openai_compatible",
    "qwen": "openai_compatible",
    "grok": "openai_compatible",
    "gemini": "gemini_native",
    "claude": "claude",
}

_DEFAULT_OPENAI_BASE = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "grok": "https://api.x.ai/v1",
}


async def get_ai_provider(model=None):
    """获取AI提供者实例"""
    if not model:
        model = DEFAULT_AI_MODEL
    
    # 加载模型到提供商的映射（使用dict格式）
    models_config = load_ai_models(type="dict")
    
    provider_name = None
    for name, models_list in (models_config or {}).items():
        if not isinstance(models_list, list):
            continue
        if model in models_list:
            provider_name = name
            break

    if not provider_name:
        raise ValueError(f"不支持的模型: {model}")

    providers_config = load_ai_providers(type="dict")
    provider_meta = providers_config.get(provider_name, {}) if isinstance(providers_config, dict) else {}
    if provider_meta and provider_meta.get("enabled") is False:
        raise ValueError(f"AI提供商已禁用: {provider_name}")

    provider_type = (provider_meta.get("type") or _DEFAULT_PROVIDER_TYPE.get(provider_name) or "openai_compatible").strip()

    if provider_type == "claude":
        return ClaudeProvider()

    if provider_type == "gemini_native":
        return GeminiProvider()

    if provider_type != "openai_compatible":
        raise ValueError(f"不支持的提供商类型: {provider_type}（provider={provider_name}）")

    if provider_name == "openai":
        return OpenAIProvider()
    if provider_name == "deepseek":
        return DeepSeekProvider()
    if provider_name == "qwen":
        return QwenProvider()
    if provider_name == "grok":
        return GrokProvider()
    if provider_name == "gemini":
        return OpenAICompatibleProvider(provider_key=provider_name, default_api_base="")

    return OpenAICompatibleProvider(
        provider_key=provider_name,
        default_api_base=_DEFAULT_OPENAI_BASE.get(provider_name, ""),
    )


__all__ = [
    'BaseAIProvider',
    'OpenAIProvider',
    'GeminiProvider',
    'DeepSeekProvider',
    'QwenProvider',
    'GrokProvider',
    'ClaudeProvider',
    'get_ai_provider'
]

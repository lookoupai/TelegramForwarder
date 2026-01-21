from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator
from openai import AsyncOpenAI

from utils.settings import load_ai_models, load_ai_providers, save_ai_models, save_ai_providers


_PROVIDER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_ALLOWED_PROVIDER_TYPES = {"openai_compatible", "gemini_native", "claude"}


def _normalize_provider_name(value: str) -> str:
    trimmed = (value or "").strip().lower()
    if not trimmed:
        raise ValueError("provider_name 不能为空")
    if not _PROVIDER_NAME_RE.match(trimmed):
        raise ValueError("provider_name 仅允许 a-z0-9._- 且长度<=64")
    return trimmed


def _mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 6:
        return "***"
    return f"{secret[:3]}***{secret[-2:]}"


def _env_key_name(provider_name: str, provider_type: str) -> str:
    if provider_type == "claude":
        return "CLAUDE_API_KEY"
    if provider_type == "gemini_native":
        return "GEMINI_API_KEY"
    return f"{provider_name.upper()}_API_KEY"


def _env_base_name(provider_name: str, provider_type: str) -> str:
    if provider_type == "claude":
        return "CLAUDE_API_BASE"
    if provider_type == "gemini_native":
        return "GEMINI_API_BASE"
    return f"{provider_name.upper()}_API_BASE"


def _normalize_models(models: Any) -> List[str]:
    if models is None:
        return []
    if not isinstance(models, list):
        raise ValueError("models 必须为数组")
    normalized: List[str] = []
    for item in models:
        model = str(item).strip()
        if not model:
            continue
        if len(model) > 128:
            raise ValueError("model 名称过长（<=128）")
        normalized.append(model)
    seen = set()
    deduped: List[str] = []
    for m in normalized:
        if m in seen:
            continue
        seen.add(m)
        deduped.append(m)
    return deduped


def _ensure_models_unique(models_config: Dict[str, List[str]]) -> None:
    used: Dict[str, str] = {}
    for provider_name, models in models_config.items():
        for model in models:
            existing = used.get(model)
            if existing and existing != provider_name:
                raise ValueError(f"模型重复：{model} 同时存在于 {existing} 与 {provider_name}")
            used[model] = provider_name


class AIProviderOut(BaseModel):
    name: str
    type: str
    enabled: bool
    api_base: str
    api_key_masked: str
    api_key_configured: bool
    api_base_configured: bool


class AIProviderUpsert(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    type: str = Field(default="openai_compatible")
    enabled: bool = True
    api_base: Optional[str] = Field(default=None, max_length=2048)
    api_key: Optional[str] = Field(default=None, max_length=4096)

    @validator("name")
    def validate_name(cls, value: str) -> str:
        return _normalize_provider_name(value)

    @validator("type")
    def validate_type(cls, value: str) -> str:
        trimmed = (value or "").strip()
        if trimmed not in _ALLOWED_PROVIDER_TYPES:
            raise ValueError(f"type 必须为: {', '.join(sorted(_ALLOWED_PROVIDER_TYPES))}")
        return trimmed

    @validator("api_base")
    def normalize_base(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return ""
        if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise ValueError("api_base 必须以 http:// 或 https:// 开头")
        return trimmed

    @validator("api_key")
    def normalize_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed


class AIModelsUpdate(BaseModel):
    models: Dict[str, List[str]]

    @validator("models")
    def validate_models(cls, value: Dict[str, List[str]]) -> Dict[str, List[str]]:
        if not isinstance(value, dict):
            raise ValueError("models 必须为对象")
        normalized: Dict[str, List[str]] = {}
        for raw_provider, raw_models in value.items():
            provider_name = _normalize_provider_name(str(raw_provider))
            normalized[provider_name] = _normalize_models(raw_models)
        _ensure_models_unique(normalized)
        return normalized


class AIProviderTestOut(BaseModel):
    ok: bool
    provider: str
    type: str
    message: str
    latency_ms: Optional[int] = None
    models_count: Optional[int] = None
    models_sample: Optional[List[str]] = None


class AIProviderSyncModelsOut(BaseModel):
    ok: bool
    provider: str
    type: str
    mode: str
    fetched: int
    added: int
    removed: int
    total: int


def list_ai_providers() -> List[AIProviderOut]:
    providers_config = load_ai_providers(type="dict")
    if not isinstance(providers_config, dict):
        providers_config = {}

    result: List[AIProviderOut] = []
    for provider_name in sorted(providers_config.keys()):
        raw = providers_config.get(provider_name) or {}
        provider_type = str(raw.get("type") or "openai_compatible").strip()
        enabled = bool(raw.get("enabled", True))
        api_base = str(raw.get("api_base") or "").strip()
        api_key = str(raw.get("api_key") or "").strip()

        env_key = _env_key_name(provider_name, provider_type)
        env_base = _env_base_name(provider_name, provider_type)
        key_configured = bool(api_key or os.getenv(env_key, "").strip())
        base_configured = bool(api_base or os.getenv(env_base, "").strip())

        result.append(
            AIProviderOut(
                name=provider_name,
                type=provider_type,
                enabled=enabled,
                api_base=api_base,
                api_key_masked=_mask_secret(api_key),
                api_key_configured=key_configured,
                api_base_configured=base_configured,
            )
        )
    return result


def upsert_ai_provider(payload: AIProviderUpsert) -> AIProviderOut:
    providers_config = load_ai_providers(type="dict")
    if not isinstance(providers_config, dict):
        providers_config = {}

    current = providers_config.get(payload.name) or {}
    provider_type = payload.type
    updated = {
        "type": provider_type,
        "enabled": bool(payload.enabled),
        "api_base": current.get("api_base", ""),
        "api_key": current.get("api_key", ""),
    }

    if payload.api_base is not None:
        updated["api_base"] = payload.api_base
    if payload.api_key is not None and payload.api_key != "":
        updated["api_key"] = payload.api_key

    providers_config[payload.name] = updated
    save_ai_providers(providers_config)

    env_key = _env_key_name(payload.name, provider_type)
    env_base = _env_base_name(payload.name, provider_type)
    key_configured = bool(str(updated.get("api_key") or "").strip() or os.getenv(env_key, "").strip())
    base_configured = bool(str(updated.get("api_base") or "").strip() or os.getenv(env_base, "").strip())

    return AIProviderOut(
        name=payload.name,
        type=provider_type,
        enabled=bool(updated.get("enabled", True)),
        api_base=str(updated.get("api_base") or "").strip(),
        api_key_masked=_mask_secret(str(updated.get("api_key") or "").strip()),
        api_key_configured=key_configured,
        api_base_configured=base_configured,
    )


def delete_ai_provider(provider_name: str) -> bool:
    name = _normalize_provider_name(provider_name)
    providers_config = load_ai_providers(type="dict")
    if not isinstance(providers_config, dict) or name not in providers_config:
        return False

    del providers_config[name]
    save_ai_providers(providers_config)

    models_config = load_ai_models(type="dict")
    if isinstance(models_config, dict) and name in models_config:
        del models_config[name]
        save_ai_models(models_config)

    return True


def get_ai_models_config() -> Dict[str, List[str]]:
    models_config = load_ai_models(type="dict")
    if not isinstance(models_config, dict):
        return {}
    normalized: Dict[str, List[str]] = {}
    for raw_provider, raw_models in models_config.items():
        provider_name = _normalize_provider_name(str(raw_provider))
        normalized[provider_name] = _normalize_models(raw_models)
    _ensure_models_unique(normalized)
    return normalized


def update_ai_models_config(payload: AIModelsUpdate) -> Dict[str, List[str]]:
    providers_config = load_ai_providers(type="dict")
    if not isinstance(providers_config, dict):
        providers_config = {}

    for provider_name in payload.models.keys():
        if provider_name not in providers_config:
            raise ValueError(f"provider 未配置: {provider_name}（请先在AI提供商中新增）")

    save_ai_models(payload.models)
    return payload.models


def _get_provider_meta(provider_name: str) -> Dict[str, Any]:
    providers_config = load_ai_providers(type="dict")
    if not isinstance(providers_config, dict):
        return {}
    return providers_config.get(provider_name, {}) or {}


def _resolve_provider_type(provider_name: str, provider_meta: Dict[str, Any]) -> str:
    provider_type = str(provider_meta.get("type") or "openai_compatible").strip()
    if provider_type not in _ALLOWED_PROVIDER_TYPES:
        raise ValueError(f"不支持的提供商类型: {provider_type}（provider={provider_name}）")
    return provider_type


def _resolve_provider_credentials(provider_name: str) -> Dict[str, str]:
    provider_meta = _get_provider_meta(provider_name)
    if provider_meta and provider_meta.get("enabled") is False:
        raise ValueError(f"AI提供商已禁用: {provider_name}")

    provider_type = _resolve_provider_type(provider_name, provider_meta)
    api_key = str(provider_meta.get("api_key") or "").strip()
    api_base = str(provider_meta.get("api_base") or "").strip()

    env_key = _env_key_name(provider_name, provider_type)
    env_base = _env_base_name(provider_name, provider_type)
    if not api_key:
        api_key = os.getenv(env_key, "").strip()
    if not api_base:
        api_base = os.getenv(env_base, "").strip()

    return {"type": provider_type, "api_key": api_key, "api_base": api_base}


async def test_ai_provider(provider_name: str) -> AIProviderTestOut:
    name = _normalize_provider_name(provider_name)
    creds = _resolve_provider_credentials(name)
    provider_type = creds["type"]

    if provider_type != "openai_compatible":
        if not creds["api_key"]:
            raise ValueError(f"未配置 {name} 的 api_key")
        return AIProviderTestOut(ok=True, provider=name, type=provider_type, message="该类型暂不支持在线测试（已检测到 api_key）")

    if not creds["api_key"]:
        raise ValueError(f"未配置 {name} 的 api_key")
    if not creds["api_base"]:
        raise ValueError(f"未配置 {name} 的 api_base（需包含 /v1）")

    start = time.perf_counter()
    client = AsyncOpenAI(api_key=creds["api_key"], base_url=creds["api_base"])
    models = await client.models.list()
    latency_ms = int((time.perf_counter() - start) * 1000)

    model_ids: List[str] = []
    data = getattr(models, "data", None)
    if isinstance(data, list):
        for item in data:
            model_id = getattr(item, "id", None)
            if model_id:
                model_ids.append(str(model_id))
    if not model_ids and isinstance(models, dict):
        for item in (models.get("data") or []):
            if isinstance(item, dict) and item.get("id"):
                model_ids.append(str(item["id"]))

    model_ids = _normalize_models(model_ids)
    return AIProviderTestOut(
        ok=True,
        provider=name,
        type=provider_type,
        message="连接成功",
        latency_ms=latency_ms,
        models_count=len(model_ids),
        models_sample=model_ids[:10],
    )


async def sync_models_from_provider(provider_name: str, mode: str = "merge") -> AIProviderSyncModelsOut:
    name = _normalize_provider_name(provider_name)
    mode = (mode or "merge").strip().lower()
    if mode not in {"merge", "replace"}:
        raise ValueError("mode 必须为 merge 或 replace")

    creds = _resolve_provider_credentials(name)
    provider_type = creds["type"]
    if provider_type != "openai_compatible":
        raise ValueError("仅支持 openai_compatible 提供商拉取模型列表")

    if not creds["api_key"]:
        raise ValueError(f"未配置 {name} 的 api_key")
    if not creds["api_base"]:
        raise ValueError(f"未配置 {name} 的 api_base（需包含 /v1）")

    client = AsyncOpenAI(api_key=creds["api_key"], base_url=creds["api_base"])
    models = await client.models.list()

    fetched_ids: List[str] = []
    data = getattr(models, "data", None)
    if isinstance(data, list):
        for item in data:
            model_id = getattr(item, "id", None)
            if model_id:
                fetched_ids.append(str(model_id))
    if not fetched_ids and isinstance(models, dict):
        for item in (models.get("data") or []):
            if isinstance(item, dict) and item.get("id"):
                fetched_ids.append(str(item["id"]))

    fetched_ids = _normalize_models(fetched_ids)
    if not fetched_ids:
        raise ValueError("未获取到任何模型（服务端未返回 data[].id）")

    providers_config = load_ai_providers(type="dict")
    if not isinstance(providers_config, dict) or name not in providers_config:
        raise ValueError(f"provider 未配置: {name}（请先在AI提供商中新增）")

    current_config = load_ai_models(type="dict")
    if not isinstance(current_config, dict):
        current_config = {}

    existing = _normalize_models(current_config.get(name, []))

    if mode == "replace":
        new_models = fetched_ids
    else:
        new_models = _normalize_models(existing + fetched_ids)

    new_config: Dict[str, List[str]] = {}
    for raw_provider, raw_models in current_config.items():
        if str(raw_provider).strip().lower() == name:
            continue
        provider_key = _normalize_provider_name(str(raw_provider))
        new_config[provider_key] = _normalize_models(raw_models)
    new_config[name] = new_models
    _ensure_models_unique(new_config)

    save_ai_models(new_config)

    existing_set = set(existing)
    new_set = set(new_models)
    fetched_set = set(fetched_ids)

    added = len(new_set - existing_set)
    removed = len(existing_set - new_set)
    return AIProviderSyncModelsOut(
        ok=True,
        provider=name,
        type=provider_type,
        mode=mode,
        fetched=len(fetched_set),
        added=added,
        removed=removed,
        total=len(new_models),
    )

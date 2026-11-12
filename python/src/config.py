"""应用配置和 OpenAI 兼容 LLM 客户端工厂。"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    value = os.getenv(key)
    return value if value not in (None, "") else default


def _env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    return int(value) if value not in (None, "") else default


def _env_float(key: str, default: float) -> float:
    value = os.getenv(key)
    return float(value) if value not in (None, "") else default


def _env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value in (None, ""):
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _is_real_key(key: str) -> bool:
    return bool(key) and not key.startswith("your_")


class Settings:
    def __init__(self) -> None:
        self.LLM_PROVIDER = _env("LLM_PROVIDER", "auto").lower()

        self.CONTRACT_LLM_API_KEY = _env("CONTRACT_LLM_API_KEY", "")
        self.CONTRACT_LLM_BASE_URL = _env(
            "CONTRACT_LLM_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.CONTRACT_LLM_MODEL = _env("CONTRACT_LLM_MODEL", "qwen-max")

        self.MINIMAX_API_KEY = _env("MINIMAX_API_KEY", "")
        self.MINIMAX_API_BASE = _env("MINIMAX_API_BASE", "https://api.minimax.chat/v1")
        self.MINIMAX_MODEL = _env("MINIMAX_MODEL", "MiniMax-M2.7")

        self.OPENAI_API_KEY = _env("OPENAI_API_KEY", "")
        self.OPENAI_API_BASE = _env("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")

        legacy_model = _env("LLM_MODEL", "")
        if legacy_model:
            if not _env("MINIMAX_MODEL", ""):
                self.MINIMAX_MODEL = legacy_model
            if not _env("OPENAI_MODEL", ""):
                self.OPENAI_MODEL = legacy_model
            if not _env("CONTRACT_LLM_MODEL", ""):
                self.CONTRACT_LLM_MODEL = legacy_model

        self.LLM_TIMEOUT = _env_int("LLM_TIMEOUT", 60)
        self.LLM_MAX_RETRIES = _env_int("LLM_MAX_RETRIES", 2)
        self.LLM_TEMPERATURE = _env_float("LLM_TEMPERATURE", 0.1)
        self.LLM_MAX_TOKENS = _env_int("LLM_MAX_TOKENS", 4096)
        self.LLM_CHUNK_CHARS = _env_int("LLM_CHUNK_CHARS", 12000)
        self.LLM_REPAIR_RETRIES = _env_int("LLM_REPAIR_RETRIES", 1)
        self.LLM_JSON_MODE = _env_bool("LLM_JSON_MODE", False)
        self.CIRCUIT_BREAKER_THRESHOLD = _env_int("CIRCUIT_BREAKER_THRESHOLD", 3)
        self.CIRCUIT_RECOVERY_TIMEOUT = _env_int("CIRCUIT_RECOVERY_TIMEOUT", 60)

        self.APP_HOST = _env("APP_HOST", "0.0.0.0")
        self.APP_PORT = _env_int("APP_PORT", 8000)
        self.LOG_LEVEL = _env("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = _env("LOG_FORMAT", "text")
        self.UPLOAD_DIR = _env("UPLOAD_DIR", "uploads")

        self.DATABASE_URL = _env(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5433/contract_review",
        )
        self.SEED_ON_STARTUP = _env_bool("SEED_ON_STARTUP", False)
        self.DB_POOL_SIZE = _env_int("DB_POOL_SIZE", 10)
        self.DB_MAX_OVERFLOW = _env_int("DB_MAX_OVERFLOW", 20)

        self.JWT_DEFAULT_SECRET = "dev-secret-change-in-production"
        self.JWT_SECRET_KEY = _env("JWT_SECRET_KEY", self.JWT_DEFAULT_SECRET)
        self.JWT_ALGORITHM = _env("JWT_ALGORITHM", "HS256")
        self.JWT_EXPIRE_MINUTES = _env_int("JWT_EXPIRE_MINUTES", 60)

        self.CORS_ORIGINS = _env("CORS_ORIGINS", "*")
        self.RATE_LIMIT_PER_MINUTE = _env_int("RATE_LIMIT_PER_MINUTE", 60)
        self.MAX_UPLOAD_SIZE_MB = _env_int("MAX_UPLOAD_SIZE_MB", 20)

    @property
    def auth_enabled(self) -> bool:
        return True

    @property
    def using_default_jwt_secret(self) -> bool:
        return self.JWT_SECRET_KEY == self.JWT_DEFAULT_SECRET

    def validate_security(self) -> list[str]:
        problems: list[str] = []
        if self.using_default_jwt_secret:
            problems.append("JWT_SECRET_KEY 仍为默认值")
        if len(self.JWT_SECRET_KEY) < 32:
            problems.append("JWT_SECRET_KEY 长度不足 32 字符")
        return problems


settings = Settings()

_PROVIDER_SPECS = (
    ("contract", "CONTRACT_LLM_API_KEY", "CONTRACT_LLM_BASE_URL", "CONTRACT_LLM_MODEL"),
    ("minimax", "MINIMAX_API_KEY", "MINIMAX_API_BASE", "MINIMAX_MODEL"),
    ("openai", "OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_MODEL"),
)


def get_llm(settings_obj: Settings | None = None):
    """构造 ChatOpenAI 客户端；未配置 Key 时抛出异常，由 Agent 走规则降级。"""
    from langchain_openai import ChatOpenAI

    s = settings_obj or settings
    provider = s.LLM_PROVIDER
    if provider == "auto":
        candidates = _PROVIDER_SPECS
    else:
        candidates = [c for c in _PROVIDER_SPECS if c[0] == provider]
        if not candidates:
            raise ValueError(f"未知的 LLM_PROVIDER: {provider}")

    for name, key_attr, base_attr, model_attr in candidates:
        api_key = getattr(s, key_attr)
        if not _is_real_key(api_key):
            continue
        extra = {}
        if s.LLM_JSON_MODE:
            extra["model_kwargs"] = {"response_format": {"type": "json_object"}}
        return ChatOpenAI(
            model=getattr(s, model_attr),
            api_key=api_key,
            base_url=getattr(s, base_attr),
            temperature=s.LLM_TEMPERATURE,
            max_tokens=s.LLM_MAX_TOKENS,
            **extra,
        )

    raise ValueError("未配置有效 LLM API Key，将使用规则降级模式")

"""
测试 settings API 的默认配置读取功能
"""
import pytest
import os

# 确保在导入前设置必要的环境变量
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://mumuai:password@localhost:5432/mumuai_novel")


def test_read_env_defaults_returns_expected_keys():
    """验证 read_env_defaults 返回所有必需的键"""
    from app.api.settings import read_env_defaults

    defaults = read_env_defaults()

    assert "api_provider" in defaults
    assert "api_key" in defaults
    assert "api_base_url" in defaults
    assert "llm_model" in defaults
    assert "temperature" in defaults
    assert "max_tokens" in defaults


def test_read_env_defaults_api_provider_is_openai():
    """验证默认 API Provider 是 openai"""
    from app.api.settings import read_env_defaults

    defaults = read_env_defaults()

    assert defaults["api_provider"] == "openai"


def test_read_env_defaults_uses_minimax_base_url():
    """验证默认使用 MiniMax API Base URL"""
    from app.api.settings import read_env_defaults

    defaults = read_env_defaults()

    assert "api.minimaxi.com" in defaults["api_base_url"]


def test_read_env_defaults_temperature_in_valid_range():
    """验证 temperature 在有效范围内 (0.0 - 2.0)"""
    from app.api.settings import read_env_defaults

    defaults = read_env_defaults()

    assert 0.0 <= defaults["temperature"] <= 2.0


def test_read_env_defaults_max_tokens_is_positive():
    """验证 max_tokens 是正整数"""
    from app.api.settings import read_env_defaults

    defaults = read_env_defaults()

    assert isinstance(defaults["max_tokens"], int)
    assert defaults["max_tokens"] > 0


def test_read_env_defaults_llm_model_is_non_empty():
    """验证 llm_model 是非空字符串"""
    from app.api.settings import read_env_defaults

    defaults = read_env_defaults()

    assert isinstance(defaults["llm_model"], str)
    assert len(defaults["llm_model"]) > 0

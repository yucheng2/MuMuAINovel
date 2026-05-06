"""
测试 AIService.call_with_json_retry 方法
TDD 风格：先写测试，再验证
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, "/Users/yuchengfan/dev/GitHub/yucheng2/MuMuAINovel/backend")

# 设置必要的环境变量
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://mumuai:password@localhost:5432/mumuai_novel")


def create_ai_service():
    """创建 AIService 实例用于测试"""
    from app.services.ai_service import AIService
    return AIService(
        api_provider="openai",
        api_key="test-api-key",
        api_base_url="https://api.minimaxi.com/v1",
        default_model="test-model",
        default_temperature=0.7,
        default_max_tokens=1000,
    )


async def test_returns_dict_when_json_is_valid_object():
    """当返回有效 JSON 对象时，返回字典"""
    ai_service = create_ai_service()
    valid_json = '{"name": "test", "value": 123}'

    with patch.object(ai_service, 'generate_text', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = {
            "content": valid_json,
            "finish_reason": "stop"
        }

        result = await ai_service.call_with_json_retry(
            prompt="test prompt",
            expected_type="object"
        )

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 123
        print("✅ test_returns_dict_when_json_is_valid_object PASSED")


async def test_returns_list_when_json_is_valid_array():
    """当返回有效 JSON 数组时，返回列表"""
    ai_service = create_ai_service()
    valid_json = '[1, 2, 3, "test"]'

    with patch.object(ai_service, 'generate_text', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = {
            "content": valid_json,
            "finish_reason": "stop"
        }

        result = await ai_service.call_with_json_retry(
            prompt="test prompt",
            expected_type="array"
        )

        assert isinstance(result, list)
        assert len(result) == 4
        print("✅ test_returns_list_when_json_is_valid_array PASSED")


async def test_retries_on_json_parse_failure():
    """当 JSON 解析失败时应该重试"""
    ai_service = create_ai_service()
    invalid_json = "这不是有效的 JSON"
    valid_json = '{"success": true}'

    with patch.object(ai_service, 'generate_text', new_callable=AsyncMock) as mock_generate:
        # 第一次返回无效 JSON，第二次返回有效 JSON
        mock_generate.side_effect = [
            {"content": invalid_json, "finish_reason": "stop"},
            {"content": valid_json, "finish_reason": "stop"},
        ]

        result = await ai_service.call_with_json_retry(
            prompt="test prompt",
            max_retries=3
        )

        assert mock_generate.call_count == 2
        assert result["success"] is True
        print("✅ test_retries_on_json_parse_failure PASSED")


async def test_raises_after_max_retries_exceeded():
    """当所有重试都失败时，应该抛出 ValueError"""
    ai_service = create_ai_service()
    invalid_json = "这不是有效的 JSON"

    with patch.object(ai_service, 'generate_text', new_callable=AsyncMock) as mock_generate:
        # 每次都返回无效 JSON
        mock_generate.return_value = {
            "content": invalid_json,
            "finish_reason": "stop"
        }

        try:
            await ai_service.call_with_json_retry(
                prompt="test prompt",
                max_retries=3
            )
            assert False, "应该抛出异常"
        except ValueError as e:
            assert "JSON 解析失败" in str(e)
            assert mock_generate.call_count == 3
            print("✅ test_raises_after_max_retries_exceeded PASSED")


async def test_raises_when_expected_object_but_got_array():
    """当期望对象但返回数组时，应该失败并重试"""
    ai_service = create_ai_service()
    array_json = '[1, 2, 3]'

    with patch.object(ai_service, 'generate_text', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = {
            "content": array_json,
            "finish_reason": "stop"
        }

        try:
            await ai_service.call_with_json_retry(
                prompt="test prompt",
                expected_type="object",
                max_retries=1  # 只重试1次，快速失败
            )
            assert False, "应该抛出异常"
        except ValueError as e:
            assert "期望对象" in str(e)
            print("✅ test_raises_when_expected_object_but_got_array PASSED")


async def test_raises_when_expected_array_but_got_object():
    """当期望数组但返回对象时，应该失败并重试"""
    ai_service = create_ai_service()
    object_json = '{"key": "value"}'

    with patch.object(ai_service, 'generate_text', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = {
            "content": object_json,
            "finish_reason": "stop"
        }

        try:
            await ai_service.call_with_json_retry(
                prompt="test prompt",
                expected_type="array",
                max_retries=1
            )
            assert False, "应该抛出异常"
        except ValueError as e:
            assert "期望数组" in str(e)
            print("✅ test_raises_when_expected_array_but_got_object PASSED")


async def test_adds_json_hint_on_retry():
    """重试时应该添加 JSON 提示"""
    ai_service = create_ai_service()
    invalid_json = "not valid"
    valid_json = '{"ok": true}'

    with patch.object(ai_service, 'generate_text', new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = [
            {"content": invalid_json, "finish_reason": "stop"},
            {"content": valid_json, "finish_reason": "stop"},
        ]

        await ai_service.call_with_json_retry(
            prompt="test prompt",
            max_retries=2
        )

        # 检查第二次调用是否包含了 JSON hint
        second_call = mock_generate.call_args_list[1]
        second_prompt = second_call.kwargs.get('prompt', '')
        assert "纯JSON" in second_prompt or "重试" in second_prompt
        print("✅ test_adds_json_hint_on_retry PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("运行 TDD 测试: call_with_json_retry")
    print("=" * 60)

    tests = [
        test_returns_dict_when_json_is_valid_object,
        test_returns_list_when_json_is_valid_array,
        test_retries_on_json_parse_failure,
        test_raises_after_max_retries_exceeded,
        test_raises_when_expected_object_but_got_array,
        test_raises_when_expected_array_but_got_object,
        test_adds_json_hint_on_retry,
    ]

    passed = 0
    failed = 0

    for test in tests:
        print(f"\n运行: {test.__name__}")
        print("-" * 40)
        try:
            asyncio.run(test())
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} passed, {failed} failed")
    print("=" * 60)

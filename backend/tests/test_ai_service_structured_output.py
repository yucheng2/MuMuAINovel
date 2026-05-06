"""
测试 AIService.call_with_structured_output 对思考块的处理
TDD 风格：先写测试
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, "/Users/yuchengfan/dev/GitHub/yucheng2/MuMuAINovel/backend")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://mumuai:password@localhost:5432/mumuai_novel")

from app.schemas.career import AICareerSystemOutput


async def test_with_structured_output_fails_on_thinking_but_fallback_succeeds():
    """
    RED: 测试 with_structured_output 遇到思考块时，fallback 能正确解析

    问题：MiniMax 等推理模型返回 <thinking> 块，
    导致 with_structured_output 抛出异常: Invalid JSON
    但 fallback 应该能处理这种情况
    """
    from app.services.ai_service import AIService

    ai_service = AIService(
        api_provider="openai",
        api_key="test-api-key",
        api_base_url="https://api.minimaxi.com/v1",
        default_model="MiniMax-M2.7-highspeed",
        default_temperature=0.7,
        default_max_tokens=1000,
    )

    # 模拟包含思考块的响应（这是 MiniMax 等推理模型会返回的内容）
    thinking_response = '''<think>
让我分析这个职业体系...
</think>

{"main_careers": [{"name": "战士", "level": 1}], "sub_careers": []}'''

    expected_result = {
        "main_careers": [{"name": "战士", "level": 1}],
        "sub_careers": []
    }

    print(f"\n输入包含思考块的响应")
    print(f"期望返回: {expected_result}")

    # Mock with_structured_output 抛出异常（模拟思考块导致的失败）
    with patch.object(ai_service, 'generate_text', new_callable=AsyncMock) as mock_generate:
        # 模拟 LLM 返回包含思考块的 JSON
        mock_generate.return_value = {
            "content": thinking_response,
            "finish_reason": "stop"
        }

        try:
            result = await ai_service.call_with_json_retry(
                prompt="生成职业体系",
                output_schema=AICareerSystemOutput,
                max_retries=3
            )
            print(f"实际返回: {result}")

            # 验证结果
            assert "main_careers" in result
            assert len(result["main_careers"]) == 1
            assert result["main_careers"][0]["name"] == "战士"
            print("✅ 测试通过: fallback 成功处理了思考块")
            return True

        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_strip_thinking_removes_thinking_blocks():
    """
    RED: 测试 _strip_thinking 函数是否能正确移除思考块
    """
    from app.services.ai_service import AIService

    ai_service = AIService(
        api_provider="openai",
        api_key="test-api-key",
        api_base_url="https://api.minimaxi.com/v1",
        default_model="test-model",
        default_temperature=0.7,
        default_max_tokens=1000,
    )

    content_with_thinking = '''<think>
让我分析一下这个问题...
</think>

{"key": "value"}</think>

<think>
用户想要我回答...
</think>

{"answer": "test"}'''

    # 获取不带思考块的纯 JSON
    result = ai_service._strip_thinking(content_with_thinking)
    print(f"\n原始内容前100字符: {content_with_thinking[:100]}")
    print(f"处理后: {result}")

    # 应该只剩下 JSON
    assert "<think>" not in result
    assert "</think>" not in result
    assert '{"key": "value"}' in result or '"answer": "test"' in result
    print("✅ _strip_thinking 正确移除思考块")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("测试: with_structured_output 处理思考块")
    print("=" * 60)

    tests = [
        test_strip_thinking_removes_thinking_blocks,
        test_with_structured_output_fails_on_thinking_but_fallback_succeeds,
    ]

    passed = 0
    failed = 0

    for test in tests:
        print(f"\n{'='*40}")
        print(f"运行: {test.__name__}")
        print("=" * 40)
        try:
            result = asyncio.run(test())
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"测试结果: {passed} passed, {failed} failed")
    print("=" * 60)

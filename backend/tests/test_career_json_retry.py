"""测试 call_with_json_retry"""
import asyncio
import os
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/GitHub/yucheng2/MuMuAINovel/backend")

from app.services.ai_service import AIService
from app.schemas.career import AICareerSystemOutput


async def test_json_retry():
    """测试 call_with_json_retry 使用 LangChain"""
    print("=" * 60)
    print("测试 call_with_json_retry")
    print("=" * 60)

    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        print("❌ 错误: MINIMAX_API_KEY 环境变量未设置")
        return False

    ai_service = AIService(
        api_provider="openai",
        api_key=api_key,
        api_base_url="https://api.minimaxi.com/v1",
        default_model="MiniMax-M2.7-highspeed",
        default_temperature=0.7,
        default_max_tokens=16384,
    )

    prompt = """生成一个简单的职业体系JSON：
{"main_careers": [{"name": "战士", "description": "战斗职业"}], "sub_careers": []}
"""

    print("\n📤 发送请求...")
    print(f"模型: {ai_service.default_model}")

    try:
        result = await ai_service.call_with_json_retry(
            prompt=prompt,
            output_schema=AICareerSystemOutput,
            max_retries=2,
            expected_type="object",
        )

        print("\n✅ 成功获取结果!")
        print(f"主职业数: {len(result.get('main_careers', []))}")
        print(f"副职业数: {len(result.get('sub_careers', []))}")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_json_retry())
    sys.exit(0 if result else 1)

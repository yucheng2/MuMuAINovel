"""测试职业体系生成 - 使用 LangChain structured output"""
import asyncio
import os
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/GitHub/yucheng2/MuMuAINovel/backend")

from app.services.ai_service import AIService
from app.schemas.career import AICareerSystemOutput


async def test_career_structured():
    """测试职业体系生成 - LangChain structured output"""
    print("=" * 60)
    print("测试职业体系生成 - LangChain Structured Output")
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

    prompt = """根据以下世界观信息，设计一个职业体系：

书名：修仙世界
类型：玄幻修仙
主题：修仙问道
简介：主角踏入修仙之路，历经磨难最终飞升

世界观设定：
- 时间背景：上古时代
- 地理位置：九州大地
- 氛围基调：神秘莫测
- 世界规则：灵气复苏

请返回纯JSON格式，包含main_careers和sub_careers。
"""

    print("\n📤 发送请求到 MiniMax API...")
    print(f"模型: {ai_service.default_model}")
    print(f"API Base: https://api.minimaxi.com/v1")

    try:
        result = await ai_service.call_with_structured_output(
            prompt=prompt,
            output_schema=AICareerSystemOutput,
            max_retries=3,
        )

        print("\n✅ 成功获取结果!")

        if hasattr(result, "model_dump"):
            data = result.model_dump()
        else:
            data = result

        main_careers = data.get("main_careers", [])
        sub_careers = data.get("sub_careers", [])

        print(f"\n主职业 ({len(main_careers)} 个):")
        for i, career in enumerate(main_careers[:5], 1):
            print(f"  {i}. {career.get('name', '未知')}")

        print(f"\n副职业 ({len(sub_careers)} 个):")
        for i, career in enumerate(sub_careers[:5], 1):
            print(f"  {i}. {career.get('name', '未知')}")

        print("\n" + "=" * 60)
        print("✅ 测试通过!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_career_structured())
    sys.exit(0 if result else 1)

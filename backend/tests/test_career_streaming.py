"""测试职业体系生成 - 流式输出"""
import asyncio
import os
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/GitHub/yucheng2/MuMuAINovel/backend")

from app.services.ai_service import AIService


async def test_career_streaming():
    """测试职业体系生成 - 流式输出"""
    print("=" * 60)
    print("测试职业体系生成 - 流式输出")
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
请返回纯JSON格式，包含main_careers和sub_careers。
"""

    print("\n📤 开始流式请求 MiniMax API...")
    print(f"模型: {ai_service.default_model}")

    full_response = ""
    chunk_count = 0

    try:
        async for chunk in ai_service.generate_text_stream(
            prompt=prompt,
            provider="openai",
            model=ai_service.default_model,
        ):
            chunk_count += 1
            full_response += chunk

            # 每20个chunk打印一次进度
            if chunk_count % 20 == 0:
                print(f"[{chunk_count}] ", end="", flush=True)
                print(repr(full_response[-30:]) if len(full_response) > 30 else repr(full_response))

        print(f"\n✅ 流式输出完成! 共 {chunk_count} 个 chunks")

        # 解析 JSON
        print("\n📋 解析 JSON 结果...")
        cleaned = ai_service._clean_json_response(full_response)
        import json
        data = json.loads(cleaned)

        main_careers = data.get("main_careers", [])
        sub_careers = data.get("sub_careers", [])

        print(f"\n✅ 解析成功! 主职业: {len(main_careers)}, 副职业: {len(sub_careers)}")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_career_streaming())
    sys.exit(0 if result else 1)

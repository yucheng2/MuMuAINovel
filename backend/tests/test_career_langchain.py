"""测试职业体系生成 - 汇总测试"""
import asyncio
import sys
import os

# 可以单独运行: python tests/test_career_structured.py
#                python tests/test_career_streaming.py
#                python tests/test_career_json_retry.py
# 或运行本文件运行所有测试

def run_structured():
    """运行 structured output 测试"""
    import sys
    sys.path.insert(0, "/Users/yuchengfan/dev/GitHub/yucheng2/MuMuAINovel/backend")
    from tests.test_career_structured import test_career_structured
    return asyncio.run(test_career_structured())

def run_streaming():
    """运行流式输出测试"""
    import sys
    sys.path.insert(0, "/Users/yuchengfan/dev/GitHub/yucheng2/MuMuAINovel/backend")
    from tests.test_career_streaming import test_career_streaming
    return asyncio.run(test_career_streaming())

def run_json_retry():
    """运行 json_retry 测试"""
    import sys
    sys.path.insert(0, "/Users/yuchengfan/dev/GitHub/yucheng2/MuMuAINovel/backend")
    from tests.test_career_json_retry import test_json_retry
    return asyncio.run(test_json_retry())

if __name__ == "__main__":
    print("=" * 60)
    print("职业体系测试 - 汇总")
    print("=" * 60)
    print()
    print("提示: 可以单独运行以下文件:")
    print("  python tests/test_career_structured.py   - structured output 测试")
    print("  python tests/test_career_streaming.py    - 流式输出测试")
    print("  python tests/test_career_json_retry.py   - json_retry 测试")
    print()

    # 检查是否指定了要运行的测试
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "structured":
            success = run_structured()
        elif test_name == "streaming":
            success = run_streaming()
        elif test_name == "json_retry":
            success = run_json_retry()
        else:
            print(f"未知测试: {test_name}")
            print("可用: structured, streaming, json_retry")
            sys.exit(1)
        sys.exit(0 if success else 1)

    # 运行所有测试
    print("运行所有测试...")
    print()

    results = {}
    results["structured"] = run_structured()
    print()
    results["streaming"] = run_streaming()
    print()
    results["json_retry"] = run_json_retry()

    print()
    print("=" * 60)
    print("测试结果汇总:")
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    print("=" * 60)

    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

"""
自动写作功能测试
"""
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend")


def test_auto_write_service_imports():
    """测试自动写作服务可以正常导入"""
    try:
        from app.services.auto_write_service import (
            auto_write_loop,
            get_project,
            get_project_word_count,
            generate_one_outline,
            expand_outline_to_chapters,
            write_chapter_content,
            get_outlines,
        )
        print("✅ test_auto_write_service_imports PASSED")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_writing_api_imports():
    """测试写作 API 可以正常导入"""
    try:
        from app.api.writing import (
            router,
            create_auto_write_task,
            stop_auto_write_task,
            get_auto_write_progress,
        )
        print("✅ test_writing_api_imports PASSED")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_get_project_word_count_query():
    """测试字数统计 SQL 查询"""
    from app.services.auto_write_service import get_project_word_count
    import inspect
    source = inspect.getsource(get_project_word_count)

    assert "func.coalesce" in source, "应该使用 coalesce 处理 NULL"
    assert "Chapter.word_count" in source, "应该查询 Chapter.word_count"
    assert "sum" in source.lower(), "应该使用 SUM 聚合"

    print("✅ test_get_project_word_count_query PASSED")
    return True


def test_auto_write_loop_function_exists():
    """测试 auto_write_loop 函数存在且是协程"""
    import inspect
    from app.services.auto_write_service import auto_write_loop

    assert inspect.iscoroutinefunction(auto_write_loop), "auto_write_loop 应该是 async 函数"

    # 检查函数签名
    sig = inspect.signature(auto_write_loop)
    params = list(sig.parameters.keys())
    assert "task_id" in params, "应该有 task_id 参数"
    assert "user_id" in params, "应该有 user_id 参数"
    assert "project_id" in params, "应该有 project_id 参数"
    assert "db" in params, "应该有 db 参数"

    print("✅ test_auto_write_loop_function_exists PASSED")
    return True


def test_api_endpoints_have_correct_decorators():
    """测试 API 端点有正确的装饰器"""
    from app.api.writing import create_auto_write_task, stop_auto_write_task, get_auto_write_progress
    import inspect

    # 检查函数是否为协程
    assert inspect.iscoroutinefunction(create_auto_write_task), "create_auto_write_task 应该是 async"
    assert inspect.iscoroutinefunction(stop_auto_write_task), "stop_auto_write_task 应该是 async"
    assert inspect.iscoroutinefunction(get_auto_write_progress), "get_auto_write_progress 应该是 async"

    print("✅ test_api_endpoints_have_correct_decorators PASSED")
    return True


def test_request_models():
    """测试请求模型"""
    from app.api.writing import AutoWriteRequest

    # 测试有效的请求
    req = AutoWriteRequest(project_id="test-uuid")
    assert req.project_id == "test-uuid"

    print("✅ test_request_models PASSED")
    return True


def test_generate_one_outline_is_async():
    """测试 generate_one_outline 是协程函数"""
    import inspect
    from app.services.auto_write_service import generate_one_outline

    assert inspect.iscoroutinefunction(generate_one_outline), "generate_one_outline 应该是 async 函数"
    print("✅ test_generate_one_outline_is_async PASSED")
    return True


def test_expand_outline_is_async():
    """测试 expand_outline_to_chapters 是协程函数"""
    import inspect
    from app.services.auto_write_service import expand_outline_to_chapters

    assert inspect.iscoroutinefunction(expand_outline_to_chapters), "expand_outline_to_chapters 应该是 async"
    print("✅ test_expand_outline_is_async PASSED")
    return True


def test_write_chapter_is_async():
    """测试 write_chapter_content 是协程函数"""
    import inspect
    from app.services.auto_write_service import write_chapter_content

    assert inspect.iscoroutinefunction(write_chapter_content), "write_chapter_content 应该是 async"
    print("✅ test_write_chapter_is_async PASSED")
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("自动写作功能测试")
    print("=" * 60)

    tests = [
        test_auto_write_service_imports,
        test_writing_api_imports,
        test_get_project_word_count_query,
        test_auto_write_loop_function_exists,
        test_api_endpoints_have_correct_decorators,
        test_request_models,
        test_generate_one_outline_is_async,
        test_expand_outline_is_async,
        test_write_chapter_is_async,
    ]

    results = []
    for test in tests:
        print(f"\n📝 Running: {test.__name__}")
        try:
            result = test()
            results.append((test.__name__, result, None))
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False, str(e)))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"      Error: {error}")
        if not result:
            all_passed = False

    print("=" * 60)
    print(f"总计: {len(results)} 测试, {sum(1 for _, r, _ in results if r)} 通过")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

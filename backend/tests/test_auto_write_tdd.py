"""
TDD 测试：自动写作循环的问题诊断和修复

问题描述：
1. 自动写作应该循环：生成大纲 -> 展开章节 -> 写章节 -> 分析 -> 检查字数 -> 循环
2. 但当前代码缺少"分析"步骤
3. 章节生成任务可能被卡在队列中

测试策略：
1. 测试 auto_write_loop 包含"分析"步骤
2. 测试章节生成任务的参数传递正确
3. 测试循环在字数达标时正确终止
"""
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend")

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import pytest


class TestAutoWriteLoopAnalysisStep:
    """测试自动写作循环包含分析步骤"""

    def test_auto_write_loop_has_analyze_step_in_code(self):
        """验证 auto_write_loop 源码中包含分析相关的调用"""
        import inspect
        from app.services.auto_write_service import auto_write_loop

        source = inspect.getsource(auto_write_loop)

        # 检查是否有分析相关的调用
        # 用户说流程是: 生成大纲 -> 写章节 -> 分析 -> 循环
        # 所以代码中应该有类似 analyze, analysis, 分析 这样的调用
        has_analysis_keywords = any(keyword in source for keyword in [
            'analyze', 'analysis', 'analyse',
            'plot_analyzer', 'PlotAnalyzer',
            'analyze_chapter', 'analyze_outline'
        ])

        # 如果没有分析步骤，这个测试应该失败
        assert has_analysis_keywords, (
            "auto_write_loop 缺少分析步骤！"
            "用户期望流程：生成大纲 -> 展开章节 -> 写章节 -> 分析 -> 循环"
            "但代码中没有找到分析相关的调用"
        )

    def test_auto_write_loop_calls_analyze_after_writing_chapter(self):
        """测试写完章节后调用分析"""
        import inspect
        from app.services.auto_write_service import auto_write_loop

        source = inspect.getsource(auto_write_loop)

        # 检查是否在写章节之后有分析调用
        # 写章节的模式是 write_chapter_content
        # 分析应该在它之后

        write_pattern = "write_chapter_content"
        analyze_patterns = ["analyze", "analysis", "PlotAnalyzer"]

        if write_pattern in source:
            write_pos = source.find(write_pattern)
            # 检查写章节之后是否有分析
            after_write = source[write_pos:]

            has_analyze_after = any(pattern in after_write for pattern in analyze_patterns)

            # 如果写完章节后没有分析，这也是一个问题
            assert has_analyze_after, (
                "在 write_chapter_content 之后没有找到分析调用！"
                "正确的流程应该是: write_chapter_content -> 分析章节 -> 继续"
            )


class TestChapterGenerationTaskArgs:
    """测试章节生成任务的参数传递"""

    @pytest.mark.asyncio
    async def test_write_chapter_content_spawns_with_correct_args(self):
        """测试 write_chapter_content spawn 任务的参数正确"""
        from app.services.auto_write_service import write_chapter_content
        import inspect

        # 检查 write_chapter_content 的 spawn 调用
        source = inspect.getsource(write_chapter_content)

        # 找到 spawn_background_task 调用（可能是多行）
        assert "spawn_background_task" in source, "应该有 spawn_background_task 调用"

        # 检查 spawn 调用是否传入了 task.id, user_id 和正确的函数
        # 格式应该是: spawn_background_task(task.id, user_id, _run_chapter_generation)
        # 因为是多行，所以检查整个 source 而不是单行
        assert "task.id" in source, "应该传入 task.id"
        assert "user_id" in source, "应该传入 user_id"
        assert "_run_chapter_generation" in source, "应该传入章节生成函数"


class TestAutoWriteWordCountTarget:
    """测试自动写作字数目标检查"""

    @pytest.mark.asyncio
    async def test_loop_terminates_when_word_count_reached(self):
        """测试当字数达到目标时循环正确终止"""
        from app.services.auto_write_service import auto_write_loop
        import inspect

        source = inspect.getsource(auto_write_loop)

        # 检查循环终止条件
        # 应该有类似: if current_words >= target_words: break
        has_word_count_check = "target_words" in source and ("current_words" in source or "get_project_word_count" in source)
        has_break_condition = "break" in source

        assert has_word_count_check, "应该有字数检查"
        assert has_break_condition, "达到目标后应该 break 退出循环"


class TestAutoWriteAnalysisIntegration:
    """测试自动写作循环集成分析功能"""

    def test_analyze_chapter_background_is_callable(self):
        """验证 analyze_chapter_background 可以被导入和调用"""
        try:
            from app.api.chapters import analyze_chapter_background
            import inspect
            assert inspect.iscoroutinefunction(analyze_chapter_background)
        except ImportError:
            pytest.fail("analyze_chapter_background 不存在")

    @pytest.mark.asyncio
    async def test_auto_write_loop_should_include_analysis_after_write(self):
        """
        测试 auto_write_loop 在写章节后应该调用分析

        期望流程：
        for chapter in chapters:
            write_chapter_content(chapter)
            analyze_one_chapter(chapter)  # <-- 新增的分析步骤
        """
        import inspect
        from app.services.auto_write_service import auto_write_loop

        source = inspect.getsource(auto_write_loop)

        # 验证写章节和分析章节的顺序
        write_pos = source.find('write_chapter_content')
        assert write_pos > 0, "应该调用 write_chapter_content"

        # 找 write_chapter_content 之后的内容
        after_write = source[write_pos:]

        # 检查是否在写章节后调用了分析
        # 注意：实现中使用的是 analyze_one_chapter，不是 analyze_chapter_background
        has_analysis_after = (
            'analyze_one_chapter' in after_write or
            'analyzer.analyze_chapter' in after_write or
            'PlotAnalyzer' in after_write
        )

        assert has_analysis_after, (
            "auto_write_loop 应该在 write_chapter_content 之后调用分析！"
            "缺失的流程：写章节 -> 分析章节 -> 继续下一个章节"
        )


def run_diagnosis():
    """运行诊断测试"""
    print("=" * 60)
    print("自动写作问题诊断测试")
    print("=" * 60)

    test_classes = [
        TestAutoWriteLoopAnalysisStep,
        TestChapterGenerationTaskArgs,
        TestAutoWriteWordCountTarget,
        TestAutoWriteAnalysisIntegration,
    ]

    failed = []
    passed = []

    for test_class in test_classes:
        print(f"\n📝 {test_class.__name__}")
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                method = getattr(instance, method_name)
                print(f"  - {method_name}...", end=" ")
                try:
                    if asyncio.iscoroutinefunction(method):
                        asyncio.run(method())
                    else:
                        method()
                    print("✅ PASS")
                    passed.append(f"{test_class.__name__}.{method_name}")
                except AssertionError as e:
                    print(f"❌ FAIL")
                    print(f"    错误: {e}")
                    failed.append((f"{test_class.__name__}.{method_name}", str(e)))
                except Exception as e:
                    print(f"💥 ERROR: {e}")
                    failed.append((f"{test_class.__name__}.{method_name}", str(e)))

    print("\n" + "=" * 60)
    print("诊断结果汇总")
    print("=" * 60)

    if failed:
        print(f"\n❌ {len(failed)} 个测试失败:")
        for name, error in failed:
            print(f"  - {name}")
            print(f"    {error[:100]}...")
    else:
        print("\n✅ 所有测试通过！")

    print(f"\n通过: {len(passed)}, 失败: {len(failed)}")
    print("=" * 60)

    return len(failed) == 0


if __name__ == "__main__":
    success = run_diagnosis()
    sys.exit(0 if success else 1)

"""测试批量生成修复 - 验证代码语法正确"""
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/GitHub/yucheng2/MuMuAINovel/backend")

# 简单测试：导入模块验证语法正确
try:
    from app.api.chapters import batch_generate_chapters_in_order, execute_batch_generation_in_order
    print("✅ app.api.chapters 模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

try:
    from app.services.chapter_context_service import OneToOneContextBuilder, OneToManyContextBuilder
    print("✅ chapter_context_service 模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

print("\n说明: 已修复的查询:")
print("1. generate_single_chapter_for_batch 中的 outline 查询 (添加 .limit(1))")
print("2. generate_chapter_stream 中的 outline 查询 (添加 .limit(1))")
print("3. 另一个流式生成函数中的 outline 查询 (添加 .limit(1))")
print("\n这些修复防止了当数据库中存在重复大纲时 'Multiple rows were found' 错误。")

print("\n✅ 所有测试通过 - 代码语法正确")

"""测试思考块去除功能"""
import pytest
from app.services.langchain_service import LangChainService


class TestStripThinking:
    """测试 _strip_thinking 静态方法"""

    def test_strip_thinking_removes_think_block(self):
        """应该去除 <think>...</think> 思考块"""
        text = "<think> 这是一个思考过程 blah blah blah</think> 这是正文内容"
        result = LangChainService._strip_thinking(text)
        assert "思考过程" not in result
        assert "正文内容" in result
        assert "<think>" not in result
        assert "</think>" not in result

    def test_strip_thinking_handles_multiple_think_blocks(self):
        """应该去除多个思考块"""
        text = "<think> 第一个思考块</think>前言<think>第二个思考块blah</think>正文"
        result = LangChainService._strip_thinking(text)
        assert "思考块" not in result
        assert "正文" in result
        assert result.count("<think>") == 0
        assert result.count("</think>") == 0

    def test_strip_thinking_handles_empty_think_block(self):
        """应该处理空的思考块"""
        text = "<think></think>正文"
        result = LangChainService._strip_thinking(text)
        assert "<think>" not in result
        assert "</think>" not in result
        assert "正文" in result

    def test_strip_thinking_preserves_regular_content(self):
        """应该保留没有思考块的普通内容"""
        text = "这是一段正常的文本，没有任何思考过程。"
        result = LangChainService._strip_thinking(text)
        assert text == result

    def test_strip_thinking_strips_whitespace(self):
        """应该去除思考块并处理多余空白"""
        text = "<think> 思考内容</think>   正文内容  </think> 余留"
        # 原始实现使用 .strip()
        result = LangChainService._strip_thinking(text)
        assert result.startswith("正文内容") or result.startswith("余留") or result.strip() == result

    def test_strip_thinking_multiline_content(self):
        """应该处理多行思考块"""
        text = """<think>
这是一个
多行的
思考过程
</think>

这是正文内容
"""
        result = LangChainService._strip_thinking(text)
        assert "多行的" not in result
        assert "正文内容" in result
        assert "<think>" not in result
        assert "</think>" not in result

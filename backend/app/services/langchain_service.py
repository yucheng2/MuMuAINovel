"""LangChain 服务封装 - 统一的 AI 接口，支持结构化输出

提供跨提供商的结构化输出能力，解决不同 AI 模型返回 JSON 的兼容性问题。
"""
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from pydantic import BaseModel

from app.logger import get_logger
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

logger = get_logger(__name__)


class LangChainService:
    """
    LangChain 统一服务封装

    支持 OpenAI 兼容 API (包括 MuMu、CiYuan、MiniMax 等) 和 Anthropic。
    使用 with_structured_output 强制 JSON 输出。
    """

    def __init__(
        self,
        api_key: str,
        api_base_url: str,
        default_model: str,
        default_temperature: float = 0.7,
        default_max_tokens: int = 16384,  # MiniMax 推理模型需要更大的 token 限制
        default_system_prompt: Optional[str] = None,
    ):
        self.api_key = api_key
        self.api_base_url = api_base_url.rstrip("/")
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.default_system_prompt = default_system_prompt

    def _create_llm(
        self,
        provider: str,
        model: str,
        temperature: float,
        max_tokens: int,
        base_url: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        根据 provider 创建对应的 LLM 实例

        Args:
            provider: 提供商名称 (openai/anthropic)
            model: 模型名称
            temperature: 温度
            max_tokens: 最大 token 数
            base_url: 可选的 base URL，覆盖默认值
            response_format: 可选的响应格式，如 {"type": "json_object"}

        Returns:
            LLM 实例
        """
        resolved_base_url = base_url or self.api_base_url

        if provider == "anthropic":
            return ChatAnthropic(
                model=model,
                api_key=self.api_key,
                temperature=temperature,
                max_tokens_to_sample=max_tokens,
            )

        # 默认使用 OpenAI 兼容接口
        extra_kwargs = {}
        if response_format:
            extra_kwargs["response_format"] = response_format

        return ChatOpenAI(
            model=model,
            api_key=self.api_key,
            base_url=resolved_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **extra_kwargs,
        )

    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> List:
        """构建消息列表"""
        messages = []
        if system_prompt or self.default_system_prompt:
            messages.append(("system", system_prompt or self.default_system_prompt))
        messages.append(("human", prompt))
        return messages

    async def generate_text(
        self,
        prompt: str,
        provider: str = "openai",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        生成文本（非流式）

        Args:
            prompt: 用户提示词
            provider: 提供商 (openai/anthropic)
            model: 模型名称
            temperature: 温度
            max_tokens: 最大 token 数
            system_prompt: 系统提示词

        Returns:
            生成的文本
        """
        llm = self._create_llm(
            provider=provider,
            model=model or self.default_model,
            temperature=temperature or self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
        )

        messages = self._build_messages(prompt, system_prompt)
        response = await llm.ainvoke(messages)

        if hasattr(response, "content"):
            return response.content
        return str(response)

    async def generate_text_stream(
        self,
        prompt: str,
        provider: str = "openai",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        生成文本（流式）

        Args:
            prompt: 用户提示词
            provider: 提供商 (openai/anthropic)
            model: 模型名称
            temperature: 温度
            max_tokens: 最大 token 数
            system_prompt: 系统提示词

        Yields:
            文本块
        """
        llm = self._create_llm(
            provider=provider,
            model=model or self.default_model,
            temperature=temperature or self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
        )
        # 启用流式
        llm.streaming = True

        messages = self._build_messages(prompt, system_prompt)

        async for chunk in llm.astream(messages):
            if hasattr(chunk, "content"):
                yield chunk.content

    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Union[type, dict],
        provider: str = "openai",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
    ) -> Any:
        """
        使用 LangChain 的 structured output 强制 JSON 输出

        Args:
            prompt: 用户提示词
            output_schema: Pydantic 模型类或 JSON schema dict
            provider: 提供商 (openai/anthropic)
            model: 模型名称
            temperature: 温度
            max_tokens: 最大 token 数
            system_prompt: 系统提示词
            max_retries: 最大重试次数

        Returns:
            结构化输出结果
        """
        import json as json_module

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                # 对于 MiniMax 等推理模型，直接调用模型获取响应，然后手动解析 JSON
                llm = self._create_llm(
                    provider=provider,
                    model=model or self.default_model,
                    temperature=temperature or self.default_temperature,
                    max_tokens=max_tokens or self.default_max_tokens,
                    response_format={"type": "json_object"},
                )

                messages = self._build_messages(prompt, system_prompt)
                response = await llm.ainvoke(messages)

                # 获取响应内容
                content = ""
                if hasattr(response, "content"):
                    content = response.content
                elif isinstance(response, str):
                    content = response

                # 剥离推理过程
                content = self._strip_thinking(content)

                # 尝试直接解析为 JSON
                try:
                    data = json_module.loads(content)
                    logger.info(f"✅ LangChain JSON 直接解析成功")
                    return data
                except json_module.JSONDecodeError:
                    pass

                # 如果直接解析失败，尝试从文本中提取 JSON
                extracted = self._extract_json(content)
                if extracted:
                    # 使用 Pydantic 模型验证
                    if isinstance(output_schema, type):
                        instance = output_schema.model_validate(extracted)
                        logger.info(f"✅ LangChain JSON 提取+验证成功")
                        return instance
                    return extracted

                raise ValueError(f"无法从响应中提取 JSON: {content[:200]}")

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ LangChain structured output 失败 (尝试 {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    continue

        raise ValueError(f"LangChain structured output 全部失败: {last_error}")

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """
        剥离文本中的推理过程 (<think>...</think>)

        Args:
            text: 包含推理过程的文本

        Returns:
            剥离推理过程后的文本
        """
        import re
        # 匹配 <think>...</think> 模式
        pattern = r'<think>[\s\S]*?</think>'
        return re.sub(pattern, '', text).strip()

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict]:
        """
        从文本中提取 JSON 对象或数组

        Args:
            text: 可能包含 JSON 的文本

        Returns:
            提取的 JSON 对象/数组，如果提取失败则返回 None
        """
        import json as json_module
        import re

        # 剥离 markdown 代码块
        text = re.sub(r'^```json\s*\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^```\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)

        # 查找 JSON 对象或数组的起始位置
        match = re.search(r'[\[{]', text)
        if not match:
            return None

        start_pos = match.start()
        if start_pos > 0:
            text = text[start_pos:]

        # 尝试找到完整的 JSON
        for end_offset in range(len(text), 0, -1):
            try:
                candidate = text[:end_offset]
                data = json_module.loads(candidate)
                return data
            except json_module.JSONDecodeError:
                continue

        return None

    async def generate_json(
        self,
        prompt: str,
        provider: str = "openai",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        生成 JSON 输出（使用 structured output）

        Args:
            prompt: 用户提示词
            provider: 提供商
            model: 模型名称
            temperature: 温度
            max_tokens: 最大 token 数
            system_prompt: 系统提示词
            max_retries: 最大重试次数

        Returns:
            JSON 对象
        """
        from pydantic import BaseModel

        class JsonOutput(BaseModel):
            """通用 JSON 输出包装"""
            data: Dict[str, Any]

        result = await self.generate_structured_output(
            prompt=prompt,
            output_schema=JsonOutput,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            max_retries=max_retries,
        )

        if hasattr(result, "data"):
            return result.data
        return result if isinstance(result, dict) else {}


# 工厂函数，从现有 AIService 配置创建 LangChainService
def create_langchain_service_from_ai_service(ai_service: "AIService") -> LangChainService:
    """
    从 AIService 配置创建 LangChainService

    Args:
        ai_service: AIService 实例

    Returns:
        LangChainService 实例
    """
    return LangChainService(
        api_key=ai_service.api_key,
        api_base_url=ai_service.api_base_url or "https://api.openai.com/v1",
        default_model=ai_service.default_model,
        default_temperature=ai_service.default_temperature,
        default_max_tokens=ai_service.default_max_tokens,
        default_system_prompt=ai_service.default_system_prompt,
    )

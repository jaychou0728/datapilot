"""LLM Adapter — abstract base for all AI model clients."""
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """统一 LLM 接口。所有模型客户端（DeepSeek/OpenAI/Qwen/Gemini）实现此接口。"""

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.7,
                   max_tokens: int = 4096) -> str:
        """发送消息，返回文本响应。"""
        ...

    async def chat_stream(self, messages: list[dict], temperature: float = 0.7,
                          max_tokens: int = 4096):
        """流式生成（默认实现回退到非流式）。子类可覆盖以实现真正的 SSE 流。"""
        text = await self.chat(messages, temperature, max_tokens)
        yield text

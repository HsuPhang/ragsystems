"""LLM 调用：DeepSeek（OpenAI 兼容协议）。

模型：deepseek-v4-flash (DeepSeek-V4)
- 中文能力强
- API 兼容 OpenAI 格式
- 价格便宜
"""
from __future__ import annotations

from functools import lru_cache

from llama_index.core.llms import ChatMessage
from llama_index.llms.openai_like import OpenAILike

from app.config import settings
from app.utils import logger


@lru_cache(maxsize=1)
def get_llm() -> OpenAILike:
    """单例 LLM。"""
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，请检查 .env 文件")

    llm = OpenAILike(
        model=settings.DEEPSEEK_MODEL,
        api_base=settings.DEEPSEEK_BASE_URL,
        api_key=settings.DEEPSEEK_API_KEY,
        is_chat_model=True,
        temperature=0.3,        # 医疗场景偏低温度，减少幻觉
        max_tokens=1024,
        timeout=60.0,
        context_window=32768,
    )
    logger.info(f"LLM 已初始化: {settings.DEEPSEEK_MODEL} @ {settings.DEEPSEEK_BASE_URL}")
    return llm


def chat(messages: list[ChatMessage], model: str | None = None) -> str:
    """同步调用 LLM，返回字符串。

    Args:
        messages: 对话消息列表
        model: 模型名，为空时使用默认模型
    """
    if model and model != settings.DEEPSEEK_MODEL:
        llm = OpenAILike(
            model=model,
            api_base=settings.DEEPSEEK_BASE_URL,
            api_key=settings.DEEPSEEK_API_KEY,
            is_chat_model=True,
            temperature=0.3,
            max_tokens=1024,
            timeout=60.0,
            context_window=32768,
        )
    else:
        llm = get_llm()
    resp = llm.chat(messages)
    return resp.message.content or ""

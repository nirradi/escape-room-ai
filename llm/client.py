"""LangChain Ollama client adapter.

This targeted implementation mirrors `test_llama.py` usage: it builds a
LangChain `ChatPromptTemplate` and `ChatOllama` model, invokes the
chain, and returns the string output. It raises `RuntimeError` if the
required packages are not installed or the invocation fails.
"""

from __future__ import annotations

from typing import Any, Dict


def generate(prompt: str, model_cfg: Dict[str, Any]) -> str:
    """Invoke LangChain Ollama and return the string output.

    Args:
        prompt: The user-level prompt string to feed to the chain.
        model_cfg: Optional dict with keys like `model`.

    Raises:
        RuntimeError: If langchain_ollama/langchain_core are missing or invocation fails.
    """
    try:
        from langchain_ollama import ChatOllama  # type: ignore
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore
        from langchain_core.output_parsers import StrOutputParser  # type: ignore
    except Exception as exc:
        raise RuntimeError("langchain_ollama or langchain_core not available") from exc

    model = None
    if isinstance(model_cfg, dict):
        model = model_cfg.get("model") or model_cfg.get("name")

    prompt_tpl = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("user", "{input}"),
    ])

    llm = ChatOllama(model=model) if model else ChatOllama()
    chain = prompt_tpl | llm | StrOutputParser()

    try:
        return chain.invoke({"input": prompt})
    except Exception as exc:
        raise RuntimeError("LLM invocation failed") from exc


def call(prompt: str, model_cfg: Dict[str, Any]) -> str:
    return generate(prompt, model_cfg)


def complete(prompt: str, model_cfg: Dict[str, Any]) -> str:
    return generate(prompt, model_cfg)

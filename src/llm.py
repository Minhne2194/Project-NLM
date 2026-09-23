from functools import lru_cache

from langchain_core.messages import HumanMessage

from src.config import settings


def _build_hf_local():
    import torch
    from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    tokenizer = AutoTokenizer.from_pretrained(settings.hf_model)
    model = AutoModelForCausalLM.from_pretrained(
        settings.hf_model,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    )
    device = (
        settings.hf_device
        if (torch.cuda.is_available() and settings.hf_device >= 0)
        else -1
    )
    text_gen = pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
        device=device,
        return_full_text=False,
    )
    text_gen.generation_config.max_new_tokens = settings.hf_max_new_tokens
    text_gen.generation_config.do_sample = settings.llm_temperature > 0
    return ChatHuggingFace(llm=HuggingFacePipeline(pipeline=text_gen))


def _build_gemini():
    from langchain_google_genai import ChatGoogleGenerativeAI

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is required when llm_provider='gemini'.")
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=settings.llm_temperature,
        google_api_key=settings.google_api_key,
    )


def _build_vllm():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.hf_model,
        openai_api_key=settings.vllm_api_key,
        openai_api_base=settings.vllm_api_base,
        temperature=settings.llm_temperature,
    )


@lru_cache(maxsize=4)
def get_llm(provider: str | None = None):
    provider = provider or settings.llm_provider
    if provider == "hf_local":
        return _build_hf_local()
    if provider == "gemini":
        return _build_gemini()
    if provider == "vllm":
        return _build_vllm()
    raise ValueError(f"Unknown llm_provider '{provider}'")


def invoke_llm(prompt: str, provider: str | None = None) -> str:
    response = get_llm(provider=provider).invoke([HumanMessage(content=prompt)])
    content = response.content
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and "text" in p:
                parts.append(p["text"])
            elif hasattr(p, "text"):
                parts.append(p.text)
        return "\n".join(parts) if parts else str(content)
    return str(content)

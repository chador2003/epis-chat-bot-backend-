from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings

def get_llm():
    """
    Initialize and return the LLM.
    Uses the vLLM provider with Qwen-2.5-7B-Instruct.
    """
    return ChatOpenAI(
        model="Qwen/Qwen2.5-7B-Instruct",
        openai_api_key="EMPTY",
        base_url=settings.VLLM_BASE_URL,
        temperature=0
    )

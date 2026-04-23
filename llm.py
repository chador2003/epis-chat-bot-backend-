from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings

def get_llm():
    # return ChatGoogleGenerativeAI(
    #     model=settings.MODEL,
    #     temperature=settings.TEMPERATURE,
    #     google_api_key=settings.GEMINI_API_KEY  # Add it here
    # )
    return ChatOpenAI(
        model = "Qwen/Qwen2.5-7B-Instruct",
        openai_api_key="EMPTY",
        base_url=settings.VLLM_BASE_URL,
        temperature=0
    )


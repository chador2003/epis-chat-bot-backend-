import logging
from fastapi.responses import StreamingResponse
from langchain_core.prompts import ChatPromptTemplate
from config import settings

logger = logging.getLogger(__name__)

async def generate_llm_stream(llm, full_prompt):
    try:
        async for chunk in llm.astream(full_prompt):
            if chunk.content:
                yield chunk.content

    except Exception as e:
        logger.error(f"Async LLM Stream error: {e}")
        yield "\n\n[ERROR: The AI generation was interrupted.]"

async def get_chat_response(vector_store, llm, query_text):
    try:
        # Hybrid search is performed by default because we set retrieval_mode=HYBRID
        retrieved_results_with_scores = await vector_store.asimilarity_search_with_score(
            query_text, 
            k=settings.TOP_K
        )
        
    except Exception as e:
        logger.error(f"Async Retrieval Failed: {e}")
        raise Exception("Database unreachable.")

    content_list = []
    for doc, score in retrieved_results_with_scores:
        text_content = doc.page_content
        source = doc.metadata.get("source", "Unknown")
        formatted_content = f"[Source: {source}]\n{text_content}"
        content_list.append(formatted_content)

    if not content_list:
        logger.warning("No relevant context found for query")
        context_text = "No relevant information found in the EPIS documentation."
    else:
        # Safer truncation: Build context chunk by chunk within the limit
        context_parts = []
        current_length = 0
        for part in content_list:
            if current_length + len(part) + 5 > settings.MAX_CONTEXT_CHARS:
                logger.warning(f"Context limit reached. Truncating remaining {len(content_list) - len(context_parts)} chunks.")
                break
            context_parts.append(part)
            current_length += len(part) + 5 # +5 for the join separator
        
        context_text = "\n\n---\n\n".join(context_parts)
        if len(context_parts) < len(content_list):
             context_text += "\n\n[Context truncated for length...]"
        
        logger.info(f"Final context length: {len(context_text)} characters ({len(context_parts)} chunks)")

    system_prompt = (
        "You are a specialized assistant for the Bhutan Electronic Patient Information System (EPIS). "
        "Your role is to help healthcare professionals navigate and use the EPIS system effectively.\n\n"
        "Guidelines:\n"
        "1. If the user sends a greeting (e.g., 'Hi', 'Hello', 'Kuzuzangpo'), greet them back warmly and professionally before addressing their query.\n"
        "2. Answer technical questions based ONLY on the provided context within the <context> tags.\n"
        "3. Provide step-by-step instructions when explaining procedures.\n"
        "4. If the answer is not in the context, clearly state 'Sorry I don't have that information in the EPIS documentation'.\n"
        "5. Be concise and professional.\n"
        "6. Use the exact terminology from the documentation.\n"
        "7. Format steps clearly with numbering when appropriate."
    )
    
    prompt_template = ChatPromptTemplate([
        ("system", system_prompt),
        ("user", "Context:\n<context>\n{context}\n</context>\n\nQuestion: {question}\n\nAnswer:")
    ])

    full_prompt = prompt_template.format_messages(
        context=context_text,
        question=query_text
    )

    return StreamingResponse(
        generate_llm_stream(llm, full_prompt), 
        media_type="text/plain"
    )

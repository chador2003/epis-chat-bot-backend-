import PyPDF2
import os
import logging

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

def extract_text(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The PDF file was not found at: {file_path}")

    text_parts = []

    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            
            if not page_text or page_text.strip() == "":
                logger.warning(f"Page {i+1} in '{file_path}' returned no text. Skipping...")
                continue
            
            text_parts.append(page_text)

    full_text = "\n".join(text_parts)

    if not full_text.strip():
        logger.warning(
            f"The extracted text for '{file_path}' is completely empty. "
            "This PDF might be scanned or image-based (OCR required)."
        )
    return full_text

def chunk_text(llm, text, max_chunk_size=8000):    

    prompt = f"""
    You are a data processing assistant specialized in content segmentation.

    Task: Please take the provided text and break it into individual chunks. 
    Each chunk must contain exactly one question and its corresponding answer.

    Rules:
    - No Merging: Even if a Q&A are short, they must remain their own independent chunk.
    - No Truncating: Do not summarize. Keep full text intact.
    - Format: Separate chunks with the delimiter: ===CHUNK_BOUNDARY===
    - Structure: Label as Q: and A:

    Input Text:
    {text}
    """

    try:
        response = llm.invoke(prompt)
        
        if hasattr(response, 'content'):
            return response.content
        return str(response)

    except Exception as e:
        logger.error(f"Error during LLM chunking: {e}")
        return ""


CHUNK_BOUNDARY = "===CHUNK_BOUNDARY==="

def parse_into_documents(raw_chunks_string, source_name="epis_faq.pdf"):
    if not raw_chunks_string or not raw_chunks_string.strip():
        logger.warning(f"Empty input received for {source_name}. Returning empty list.")
        return []

    raw_list = raw_chunks_string.split(CHUNK_BOUNDARY)

    clean_chunks = []
    for c in raw_list:
        stripped_content = c.strip()
        if stripped_content:
            clean_chunks.append(stripped_content)
        num_chunks = len(clean_chunks)

    if num_chunks == 0:
        logger.warning(
            f"Parsing failed for {source_name}: No chunks found. "
            "The LLM response may have been malformed or empty."
        )
    elif num_chunks == 1:
        logger.warning(
            f"Parsing warning for {source_name}: Only 1 chunk detected. "
            "The LLM likely ignored the '===CHUNK_BOUNDARY===' instruction."
        )
    else:
        logger.info(f"Successfully parsed {num_chunks} documents from {source_name}.")

    documents = []
    for index, chunk in enumerate(clean_chunks):
        doc_object = Document(
            page_content=chunk,
            metadata={
                "source": source_name,
                "chunk_index": index 
            }
        )
        documents.append(doc_object)
        
    return documents

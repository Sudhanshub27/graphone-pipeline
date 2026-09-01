import re
from typing import Callable, List, Optional
import structlog
import tiktoken

logger = structlog.get_logger(__name__)

# Heuristic & Safety Constants
DEFAULT_MAX_INPUT_TOKENS = 6000
HARD_CAP_MAX_TOKENS = 12000


def estimate_token_count(text: str, model_encoding: str = "cl100k_base") -> int:
    """
    Estimate token count for input text using tiktoken when available,
    falling back to a standard len(text)/4 character heuristic.
    """
    if not text:
        return 0

    try:
        encoding = tiktoken.get_encoding(model_encoding)
        return len(encoding.encode(text))
    except Exception:
        # Fallback character heuristic: ~4 characters per token
        return max(1, len(text) // 4)


def split_text_on_semantic_boundaries(
    text: str,
    max_chunk_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
) -> List[str]:
    """
    Split text into semantically cohesive chunks based on paragraph and section
    breaks rather than mid-sentence cuts, ensuring token bounds are strictly respected.
    """
    total_tokens = estimate_token_count(text)
    if total_tokens <= max_chunk_tokens:
        return [text]

    # Primary split on double newlines / paragraph boundaries
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue

        para_tokens = estimate_token_count(para_clean)

        # If a single paragraph exceeds max_chunk_tokens, split it on sentence boundaries
        if para_tokens > max_chunk_tokens:
            sentences = re.split(r"(?<=[.!?])\s+", para_clean)
            for sentence in sentences:
                sent_tokens = estimate_token_count(sentence)
                if current_tokens + sent_tokens > max_chunk_tokens and current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = [sentence]
                    current_tokens = sent_tokens
                else:
                    current_chunk.append(sentence)
                    current_tokens += sent_tokens
        else:
            if current_tokens + para_tokens > max_chunk_tokens and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para_clean]
                current_tokens = para_tokens
            else:
                current_chunk.append(para_clean)
                current_tokens += para_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    logger.info(
        "Split document into semantic chunks",
        original_tokens=total_tokens,
        chunk_count=len(chunks),
        max_chunk_tokens=max_chunk_tokens,
    )
    return chunks


async def summarize_oversized_document(
    text: str,
    llm_summarizer_func: Optional[Callable[[str], Any]] = None,
) -> str:
    """
    Dense summary fallback strategy for oversized documents (>12,000 tokens / HTTP 413 risk).
    Extracts high-density structured summary text prior to schema extraction.
    """
    token_count = estimate_token_count(text)
    logger.warning(
        "Document exceeds hard token threshold, executing dense summary fallback path",
        token_count=token_count,
        hard_cap=HARD_CAP_MAX_TOKENS,
    )

    if llm_summarizer_func:
        try:
            summary = await llm_summarizer_func(
                f"Extract a comprehensive, dense summary retaining all key entity details, names, numbers, dates, and attributes from this text:\n\n{text[:40000]}"
            )
            if isinstance(summary, str) and len(summary) > 50:
                return summary
        except Exception as e:
            logger.error("LLM summarization fallback failed, using truncation", error=str(e))

    # Deterministic fallback: extract first 3000 tokens and last 2000 tokens
    paragraphs = text.split("\n\n")
    selected: List[str] = []
    current_tokens = 0

    for p in paragraphs:
        tokens = estimate_token_count(p)
        if current_tokens + tokens <= DEFAULT_MAX_INPUT_TOKENS:
            selected.append(p)
            current_tokens += tokens
        else:
            break

    dense_text = "\n\n".join(selected)
    logger.info(
        "Created dense summary fallback",
        original_tokens=token_count,
        summary_tokens=estimate_token_count(dense_text),
    )
    return dense_text

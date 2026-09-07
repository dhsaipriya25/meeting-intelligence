"""
Detailed Explainer agent: generates a comprehensive explanation of the content.
Used in content_analysis mode.
"""

from services.llm_client import groq_generate, chunk_text, map_reduce

SYSTEM = "You are an expert educator and content analyst. Be thorough, clear, and well-structured."

EXPLAIN_PROMPT = """\
Provide a detailed explanation of the content from the following transcript.
Break down all key concepts, ideas, and topics covered. Explain each one clearly and thoroughly.

Structure your response as:

Main Topic Overview
(2-3 sentences describing what this content is about)

Key Concepts Explained
(For each concept: name it, then explain it in detail — what it is, why it matters, how it works)

Important Points to Remember
- bullet list of the most important takeaways

Context and Background
(Any relevant background or context mentioned that helps understand the content)

TRANSCRIPT:
{transcript}
"""

CHUNK_PROMPT = """\
Provide a detailed explanation of the key concepts and ideas from this portion of content.
Focus on what is being explained, how things work, and important details.

CONTENT CHUNK:
{chunk}
"""

REDUCE_PROMPT = """\
Combine these partial explanations into one comprehensive, well-structured explanation.
Remove duplicates. Keep all important details.

Structure the final response as:
Main Topic Overview
Key Concepts Explained
Important Points to Remember
Context and Background
"""


def run(state: dict) -> dict:
    transcript = state.get("transcript", "") or ""
    words = transcript.split()

    if len(words) <= 8000:
        prompt = EXPLAIN_PROMPT.format(transcript=transcript)
        explanation = groq_generate(prompt, system=SYSTEM)
    else:
        chunks = chunk_text(transcript, chunk_size=8000, overlap=300)
        explanation = map_reduce(
            chunks=chunks,
            chunk_prompt_fn=lambda c: CHUNK_PROMPT.format(chunk=c),
            reduce_prompt=REDUCE_PROMPT,
            system=SYSTEM,
        )

    state["detailed_explanation"] = explanation
    return state

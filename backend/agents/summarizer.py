"""
Summarizer agent: produces a structured meeting summary.
Handles both short transcripts (single LLM call) and long ones (map-reduce).
"""

from services.llm_client import groq_generate, chunk_text, map_reduce

SYSTEM = "You are an expert meeting analyst. Be concise and professional."

SUMMARY_PROMPT_TEMPLATE = """\
Extract a structured summary from the following meeting transcript.
Include these sections:

Overview
(2-3 sentences describing what this meeting was about)

Key Topics Discussed
- bullet point list of main topics

Key Decisions Made
- bullet point list of decisions (write "None recorded" if none)

Participants Mentioned
- bullet point list of names/roles mentioned (write "Not identified" if unclear)

TRANSCRIPT:
{transcript}
"""

CHUNK_PROMPT_TEMPLATE = """\
Summarise the key information from this portion of a meeting transcript.
Focus on topics discussed, decisions made, and any participants mentioned.

TRANSCRIPT CHUNK:
{chunk}
"""

REDUCE_PROMPT = """\
You have been given partial summaries from different sections of a long meeting transcript.
Combine them into one coherent, structured summary with the following sections:

Overview
(2-3 sentences describing what this meeting was about)

Key Topics Discussed
- bullet points

Key Decisions Made
- bullet points (write "None recorded" if none)

Participants Mentioned
- bullet points (write "Not identified" if none identified)

Remove duplicates. Be concise and professional.
"""


def run(state: dict) -> dict:
    """
    Summarizer agent node.
    Reads state["transcript"], writes state["summary"].
    """
    transcript = state.get("transcript", "") or ""

    words = transcript.split()

    if len(words) <= 8000:
        prompt = SUMMARY_PROMPT_TEMPLATE.format(transcript=transcript)
        summary = groq_generate(prompt, system=SYSTEM)
    else:
        chunks = chunk_text(transcript, chunk_size=8000, overlap=300)

        def chunk_prompt_fn(chunk: str) -> str:
            return CHUNK_PROMPT_TEMPLATE.format(chunk=chunk)

        summary = map_reduce(
            chunks=chunks,
            chunk_prompt_fn=chunk_prompt_fn,
            reduce_prompt=REDUCE_PROMPT,
            system=SYSTEM,
        )

    state["summary"] = summary
    state["status"] = "summarizing"
    return state

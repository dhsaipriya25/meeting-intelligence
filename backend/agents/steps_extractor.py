"""
Steps Extractor agent: extracts and details step-by-step processes if present.
If no steps exist in the content, sets steps_detail to None.
Used in content_analysis mode.
"""

from services.llm_client import groq_generate

SYSTEM = "You are an expert at identifying and documenting step-by-step processes and procedures."

STEPS_PROMPT = """\
Analyze the following transcript and determine if it contains any step-by-step processes,
tutorials, instructions, procedures, or methodologies.

If the content DOES contain steps or a process, extract and detail each step clearly:
- Number each step
- Give each step a clear title
- Provide a detailed explanation of what the step involves
- Include any tips, warnings, or important notes for that step

If the content does NOT contain any steps or processes, respond with exactly this single word:
NO_STEPS

TRANSCRIPT:
{transcript}
"""


def run(state: dict) -> dict:
    transcript = state.get("transcript", "") or ""
    # Use first 15000 chars to keep within token limits
    prompt = STEPS_PROMPT.format(transcript=transcript[:15000])
    result = groq_generate(prompt, system=SYSTEM)

    if result.strip().upper().startswith("NO_STEPS"):
        state["steps_detail"] = None
    else:
        state["steps_detail"] = result.strip()

    return state

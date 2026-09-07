"""
Risk analyzer agent: identifies risks, dependencies, and blockers from the transcript.
"""

import json
import re

from services.llm_client import groq_generate, chunk_text

SYSTEM = "You are an expert project risk analyst. Be thorough and precise."

ANALYZE_PROMPT_TEMPLATE = """\
Identify all risks, dependencies, and blockers from this meeting transcript.
Return ONLY a valid JSON array. Do not include any explanation or markdown.

Each object in the array must have exactly these fields:
- "description": string (clear description of the risk/dependency/blocker)
- "category": one of "risk" | "dependency" | "blocker"
- "severity": one of "High" | "Medium" | "Low"
- "mitigation": string (suggested action to address this item)

If there are no risks, dependencies, or blockers, return an empty array: []

TRANSCRIPT:
{transcript}
"""

CHUNK_ANALYZE_TEMPLATE = """\
Identify risks, dependencies, and blockers from this portion of a meeting transcript.
Return ONLY a valid JSON array. Do not include any explanation or markdown.

Each object must have:
- "description": string
- "category": "risk" | "dependency" | "blocker"
- "severity": "High" | "Medium" | "Low"
- "mitigation": string

Return [] if none found.

TRANSCRIPT CHUNK:
{chunk}
"""

DEDUPLICATE_PROMPT = """\
Below are risks/dependencies/blockers extracted from multiple chunks of a meeting transcript.
Some may be duplicates or near-duplicates.

Combine them into a single deduplicated JSON array.
Return ONLY the JSON array — no explanation, no markdown fences.

Each object must have:
- "description": string
- "category": "risk" | "dependency" | "blocker"
- "severity": "High" | "Medium" | "Low"
- "mitigation": string

Merge duplicates, keeping the most complete and actionable information.
"""


def _parse_json_list(raw: str) -> list:
    """Parse a JSON array from LLM output, stripping markdown fences."""
    text = re.sub(r"```(?:json)?", "", raw).strip()
    text = text.strip("`").strip()

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []

    json_str = text[start : end + 1]
    try:
        result = json.loads(json_str)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError:
        return []


def run(state: dict) -> dict:
    """
    Risk analyzer node.
    Reads state["transcript"], writes state["risks"].
    """
    transcript = state.get("transcript", "") or ""
    words = transcript.split()

    if len(words) <= 8000:
        prompt = ANALYZE_PROMPT_TEMPLATE.format(transcript=transcript)
        raw = groq_generate(prompt, system=SYSTEM)
        risks = _parse_json_list(raw)
    else:
        chunks = chunk_text(transcript, chunk_size=8000, overlap=300)

        all_items: list = []
        for chunk in chunks:
            prompt = CHUNK_ANALYZE_TEMPLATE.format(chunk=chunk)
            raw = groq_generate(prompt, system=SYSTEM)
            items = _parse_json_list(raw)
            all_items.extend(items)

        if not all_items:
            state["risks"] = []
            return state

        combined_json = json.dumps(all_items, indent=2)
        reduce_prompt = (
            f"{DEDUPLICATE_PROMPT}\n\nCombined items from all chunks:\n\n"
            f"{combined_json}"
        )
        raw_deduped = groq_generate(reduce_prompt, system=SYSTEM)
        risks = _parse_json_list(raw_deduped)

        if not risks:
            risks = all_items

    state["risks"] = risks
    return state

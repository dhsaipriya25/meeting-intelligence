"""
Action extractor agent: pulls action items from the meeting transcript.
Returns a list of structured dicts.
"""

import json
import re

from services.llm_client import groq_generate, chunk_text, map_reduce

SYSTEM = "You are an expert meeting analyst. Extract actionable tasks precisely."

EXTRACT_PROMPT_TEMPLATE = """\
Extract ALL action items from this meeting transcript.
Return ONLY a valid JSON array. Do not include any explanation or markdown.

Each object in the array must have exactly these fields:
- "task": string (what needs to be done)
- "assignee": string (person responsible, use "TBD" if unclear)
- "due_date": string (ISO date like "2024-02-15") or null if not mentioned
- "priority": one of "High", "Medium", "Low"
- "context": string (one sentence explaining the context of this task)

If there are no action items, return an empty array: []

TRANSCRIPT:
{transcript}
"""

CHUNK_EXTRACT_TEMPLATE = """\
Extract ALL action items from this portion of a meeting transcript.
Return ONLY a valid JSON array. Do not include any explanation or markdown.

Each object must have:
- "task": string
- "assignee": string (use "TBD" if unclear)
- "due_date": string (ISO date) or null
- "priority": "High" | "Medium" | "Low"
- "context": string (one sentence)

Return [] if no action items found in this chunk.

TRANSCRIPT CHUNK:
{chunk}
"""

DEDUPLICATE_PROMPT = """\
Below are action items extracted from multiple chunks of a meeting transcript.
Some may be duplicates or near-duplicates.

Combine them into a single deduplicated JSON array.
Return ONLY the JSON array — no explanation, no markdown fences.

Each object must have:
- "task": string
- "assignee": string
- "due_date": string or null
- "priority": "High" | "Medium" | "Low"
- "context": string

Merge duplicates, keeping the most complete information.
"""


def _parse_json_list(raw: str) -> list:
    """
    Parse a JSON array from LLM output, stripping markdown code fences.
    Returns an empty list on any parsing error.
    """
    # Strip markdown fences
    text = re.sub(r"```(?:json)?", "", raw).strip()
    text = text.strip("`").strip()

    # Find the first '[' and last ']'
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
    Action extractor node.
    Reads state["transcript"], writes state["action_items"].
    """
    transcript = state.get("transcript", "") or ""
    words = transcript.split()

    if len(words) <= 8000:
        prompt = EXTRACT_PROMPT_TEMPLATE.format(transcript=transcript)
        raw = groq_generate(prompt, system=SYSTEM)
        action_items = _parse_json_list(raw)
    else:
        chunks = chunk_text(transcript, chunk_size=8000, overlap=300)

        def chunk_prompt_fn(chunk: str) -> str:
            return CHUNK_EXTRACT_TEMPLATE.format(chunk=chunk)

        # For JSON extraction we do map step manually to collect JSON arrays,
        # then pass them as a combined list to the deduplicate reduce step.
        all_items: list = []
        for chunk in chunks:
            prompt = chunk_prompt_fn(chunk)
            raw = groq_generate(prompt, system=SYSTEM)
            items = _parse_json_list(raw)
            all_items.extend(items)

        if not all_items:
            state["action_items"] = []
            return state

        # Deduplicate via a reduce LLM call
        combined_json = json.dumps(all_items, indent=2)
        reduce_prompt = (
            f"{DEDUPLICATE_PROMPT}\n\nCombined action items from all chunks:\n\n"
            f"{combined_json}"
        )
        raw_deduped = groq_generate(reduce_prompt, system=SYSTEM)
        action_items = _parse_json_list(raw_deduped)

        # Fallback: if dedup LLM returned nothing, use the raw collected list
        if not action_items:
            action_items = all_items

    state["action_items"] = action_items
    return state

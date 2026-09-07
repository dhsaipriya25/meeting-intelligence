"""
Email drafter agent: composes a professional follow-up email
based on the meeting summary and action items.
"""

from services.llm_client import groq_generate

SYSTEM = (
    "You are a professional business communication expert. "
    "Write clear, concise, and professional emails."
)

EMAIL_PROMPT_TEMPLATE = """\
Write a professional follow-up email based on the meeting information below.

The email must have exactly this structure:
1. Subject: line (e.g. "Subject: Follow-up: [Meeting Topic] — Action Items & Next Steps")
2. A blank line
3. Dear Team / Hi [relevant greeting],
4. A brief paragraph summarising what the meeting covered (2-3 sentences)
5. A blank line
6. "Action Items:" header, then a numbered list of each action item with owner and due date:
   1. [Task] — Owner: [Assignee] | Due: [due_date or "TBD"]
7. A blank line
8. A brief closing paragraph with next steps / call to action
9. Sign-off:
   Best regards,
   [Your Name]
   Meeting Intelligence System

--- MEETING SUMMARY ---
{summary}

--- ACTION ITEMS ---
{action_items_text}
"""


def _format_action_items(action_items: list) -> str:
    if not action_items:
        return "No action items recorded."
    lines = []
    for i, item in enumerate(action_items, start=1):
        task = item.get("task", "")
        assignee = item.get("assignee", "TBD")
        due_date = item.get("due_date") or "TBD"
        lines.append(f"{i}. {task} — Owner: {assignee} | Due: {due_date}")
    return "\n".join(lines)


def run(state: dict) -> dict:
    """
    Email drafter node.
    Reads state["summary"], state["action_items"].
    Writes state["email_draft"].
    """
    summary = state.get("summary", "") or "No summary available."
    action_items = state.get("action_items") or []

    action_items_text = _format_action_items(action_items)

    prompt = EMAIL_PROMPT_TEMPLATE.format(
        summary=summary,
        action_items_text=action_items_text,
    )

    email_draft = groq_generate(prompt, system=SYSTEM)
    state["email_draft"] = email_draft
    return state

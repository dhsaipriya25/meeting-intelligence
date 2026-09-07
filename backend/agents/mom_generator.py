"""
Minutes of Meeting (MOM) generator agent.
Uses summary + action_items + risks (NOT raw transcript) as context.
Produces a plain-text MOM document with clear section headers.
"""

import json
from datetime import datetime

from services.llm_client import groq_generate

SYSTEM = "You are an expert meeting secretary. Write clear, professional Minutes of Meeting."

MOM_PROMPT_TEMPLATE = """\
Generate a complete Minutes of Meeting (MOM) document using the information provided below.
Use plain text — NOT markdown. Use section headers in ALL CAPS followed by a line of === characters.

The document must have these sections in order:
1. MINUTES OF MEETING  (main title)
2. MEETING SUMMARY
3. KEY DISCUSSION POINTS
4. DECISIONS MADE
5. ACTION ITEMS  (format each as: [Priority] Task — Assignee (Due: date))
6. RISKS & DEPENDENCIES  (format each as: [Severity][Category] Description — Mitigation: ...)
7. NEXT STEPS
8. Prepared By: AI Meeting Intelligence System  |  Date: {date}

Use === underlines under each section header.
Be thorough, professional, and well-structured.

--- MEETING SUMMARY ---
{summary}

--- ACTION ITEMS ---
{action_items_text}

--- RISKS & DEPENDENCIES ---
{risks_text}
"""


def _format_action_items(action_items: list) -> str:
    if not action_items:
        return "No action items recorded."
    lines = []
    for i, item in enumerate(action_items, start=1):
        task = item.get("task", "")
        assignee = item.get("assignee", "TBD")
        due_date = item.get("due_date") or "No deadline"
        priority = item.get("priority", "Medium")
        context = item.get("context", "")
        lines.append(
            f"{i}. [{priority}] {task}\n"
            f"   Assignee: {assignee} | Due: {due_date}\n"
            f"   Context: {context}"
        )
    return "\n\n".join(lines)


def _format_risks(risks: list) -> str:
    if not risks:
        return "No risks or dependencies recorded."
    lines = []
    for i, item in enumerate(risks, start=1):
        desc = item.get("description", "")
        category = item.get("category", "risk").capitalize()
        severity = item.get("severity", "Medium")
        mitigation = item.get("mitigation", "No mitigation specified.")
        lines.append(
            f"{i}. [{severity}][{category}] {desc}\n"
            f"   Mitigation: {mitigation}"
        )
    return "\n\n".join(lines)


def run(state: dict) -> dict:
    """
    MOM generator node.
    Reads state["summary"], state["action_items"], state["risks"].
    Writes state["mom_document"].
    """
    summary = state.get("summary", "") or "No summary available."
    action_items = state.get("action_items") or []
    risks = state.get("risks") or []

    action_items_text = _format_action_items(action_items)
    risks_text = _format_risks(risks)
    today = datetime.now().strftime("%B %d, %Y")

    prompt = MOM_PROMPT_TEMPLATE.format(
        date=today,
        summary=summary,
        action_items_text=action_items_text,
        risks_text=risks_text,
    )

    mom_document = groq_generate(prompt, system=SYSTEM)
    state["mom_document"] = mom_document
    return state

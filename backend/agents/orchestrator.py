"""
LangGraph orchestrator — supports two pipeline modes:

  meeting_analysis  : transcribe → summarize → extract_actions → analyze_risks
                      → generate_mom → draft_email → finalize

  content_analysis  : transcribe → summarize → explain → extract_steps → finalize
"""

import traceback
from typing import Optional, Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

import job_store
from services import transcription
from agents import (
    summarizer,
    action_extractor,
    risk_analyzer,
    mom_generator,
    email_drafter,
    detailed_explainer,
    steps_extractor,
)


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class MeetingState(TypedDict):
    job_id: str
    input_type: str
    output_mode: str          # "meeting_analysis" | "content_analysis"
    audio_path: Optional[str]
    raw_text: Optional[str]
    transcript: Optional[str]
    summary: Optional[str]
    # meeting_analysis outputs
    action_items: Optional[list]
    risks: Optional[list]
    mom_document: Optional[str]
    email_draft: Optional[str]
    # content_analysis outputs
    detailed_explanation: Optional[str]
    steps_detail: Optional[str]
    status: str
    error: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fail(state: MeetingState, msg: str) -> MeetingState:
    print(f"[NODE] ERROR: {msg}", flush=True)
    traceback.print_exc()
    state["error"] = msg
    state["status"] = "failed"
    return state


# ---------------------------------------------------------------------------
# Shared nodes
# ---------------------------------------------------------------------------

def node_transcribe(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    print(f"[NODE] transcribe | input_type={state.get('input_type')} | mode={state.get('output_mode')}", flush=True)
    try:
        job_store.update_job(job_id, status="transcribing", progress=10, current_agent="Transcription")
        input_type = state.get("input_type", "")

        if input_type in ("text_file", "raw_text"):
            transcript = state.get("raw_text") or ""
            if not transcript:
                raise ValueError("No text content provided.")

        elif input_type == "youtube":
            from services.ingestion import get_youtube_transcript, download_youtube
            url = state.get("raw_text")
            if not url:
                raise ValueError("No YouTube URL provided.")
            print("[NODE] Trying YouTube captions API...", flush=True)
            transcript = get_youtube_transcript(url)
            if transcript:
                print(f"[NODE] Got captions ({len(transcript)} chars)", flush=True)
            else:
                print("[NODE] No captions — falling back to audio download...", flush=True)
                audio_path = download_youtube(url, job_id)
                transcript = transcription.transcribe(audio_path)

        else:
            audio_path = state.get("audio_path")
            if not audio_path:
                raise ValueError("No audio path provided.")
            transcript = transcription.transcribe(audio_path)

        job_store.update_job(job_id, transcript=transcript, progress=20)
        state["transcript"] = transcript
        state["status"] = "transcribing"
        return state

    except Exception as exc:
        return _fail(state, f"Transcription failed: {exc}")


def node_summarize(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    print("[NODE] summarize", flush=True)
    try:
        job_store.update_job(job_id, status="summarizing", progress=30, current_agent="Summarizer")
        state = summarizer.run(state)
        job_store.update_job(job_id, summary=state.get("summary"), progress=40)
        return state
    except Exception as exc:
        return _fail(state, f"Summarization failed: {exc}")


def node_finalize(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    print("[NODE] finalize", flush=True)
    job_store.update_job(
        job_id,
        status="completed",
        progress=100,
        current_agent="",
        transcript=state.get("transcript"),
        summary=state.get("summary"),
        output_mode=state.get("output_mode", "meeting_analysis"),
        # meeting_analysis
        action_items=state.get("action_items"),
        risks=state.get("risks"),
        mom_document=state.get("mom_document"),
        email_draft=state.get("email_draft"),
        # content_analysis
        detailed_explanation=state.get("detailed_explanation"),
        steps_detail=state.get("steps_detail"),
    )
    state["status"] = "completed"
    return state


def node_error(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    error_msg = state.get("error", "Unknown pipeline error.")
    print(f"[NODE] error: {error_msg}", flush=True)
    job_store.update_job(job_id, status="failed", progress=0, current_agent="", error=error_msg)
    state["status"] = "failed"
    return state


# ---------------------------------------------------------------------------
# Meeting Analysis nodes
# ---------------------------------------------------------------------------

def node_extract_actions(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    print("[NODE] extract_actions", flush=True)
    try:
        job_store.update_job(job_id, status="extracting_actions", progress=50, current_agent="Action Extractor")
        state = action_extractor.run(state)
        job_store.update_job(job_id, action_items=state.get("action_items"), progress=60)
        return state
    except Exception as exc:
        return _fail(state, f"Action extraction failed: {exc}")


def node_analyze_risks(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    print("[NODE] analyze_risks", flush=True)
    try:
        job_store.update_job(job_id, status="analyzing_risks", progress=65, current_agent="Risk Analyzer")
        state = risk_analyzer.run(state)
        job_store.update_job(job_id, risks=state.get("risks"), progress=75)
        return state
    except Exception as exc:
        return _fail(state, f"Risk analysis failed: {exc}")


def node_generate_mom(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    print("[NODE] generate_mom", flush=True)
    try:
        job_store.update_job(job_id, status="generating_mom", progress=80, current_agent="MOM Generator")
        state = mom_generator.run(state)
        job_store.update_job(job_id, mom_document=state.get("mom_document"), progress=88)
        return state
    except Exception as exc:
        return _fail(state, f"MOM generation failed: {exc}")


def node_draft_email(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    print("[NODE] draft_email", flush=True)
    try:
        job_store.update_job(job_id, status="drafting_email", progress=92, current_agent="Email Drafter")
        state = email_drafter.run(state)
        job_store.update_job(job_id, email_draft=state.get("email_draft"), progress=95)
        return state
    except Exception as exc:
        return _fail(state, f"Email drafting failed: {exc}")


# ---------------------------------------------------------------------------
# Content Analysis nodes
# ---------------------------------------------------------------------------

def node_explain(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    print("[NODE] explain", flush=True)
    try:
        job_store.update_job(job_id, status="explaining", progress=55, current_agent="Detailed Explainer")
        state = detailed_explainer.run(state)
        job_store.update_job(job_id, detailed_explanation=state.get("detailed_explanation"), progress=75)
        return state
    except Exception as exc:
        return _fail(state, f"Explanation failed: {exc}")


def node_extract_steps(state: MeetingState) -> MeetingState:
    job_id = state["job_id"]
    print("[NODE] extract_steps", flush=True)
    try:
        job_store.update_job(job_id, status="extracting_steps", progress=85, current_agent="Steps Extractor")
        state = steps_extractor.run(state)
        job_store.update_job(job_id, steps_detail=state.get("steps_detail"), progress=95)
        return state
    except Exception as exc:
        return _fail(state, f"Steps extraction failed: {exc}")


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _on_fail(state: MeetingState) -> Literal["error", "__next__"]:
    return "error" if state.get("status") == "failed" else "__next__"


def _route_after_summarize(state: MeetingState) -> str:
    if state.get("status") == "failed":
        return "error"
    return "explain" if state.get("output_mode") == "content_analysis" else "extract_actions"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_graph() -> StateGraph:
    g = StateGraph(MeetingState)

    # Nodes
    g.add_node("transcribe",      node_transcribe)
    g.add_node("summarize",       node_summarize)
    g.add_node("finalize",        node_finalize)
    g.add_node("error",           node_error)
    # Meeting Analysis
    g.add_node("extract_actions", node_extract_actions)
    g.add_node("analyze_risks",   node_analyze_risks)
    g.add_node("generate_mom",    node_generate_mom)
    g.add_node("draft_email",     node_draft_email)
    # Content Analysis
    g.add_node("explain",         node_explain)
    g.add_node("extract_steps",   node_extract_steps)

    # Entry
    g.add_edge(START, "transcribe")
    g.add_conditional_edges("transcribe", _on_fail, {"error": "error", "__next__": "summarize"})

    # Branch after summarize
    g.add_conditional_edges("summarize", _route_after_summarize,
                            {"error": "error", "explain": "explain", "extract_actions": "extract_actions"})

    # Meeting Analysis path
    g.add_conditional_edges("extract_actions", _on_fail, {"error": "error", "__next__": "analyze_risks"})
    g.add_conditional_edges("analyze_risks",   _on_fail, {"error": "error", "__next__": "generate_mom"})
    g.add_conditional_edges("generate_mom",    _on_fail, {"error": "error", "__next__": "draft_email"})
    g.add_conditional_edges("draft_email",     _on_fail, {"error": "error", "__next__": "finalize"})

    # Content Analysis path
    g.add_conditional_edges("explain",         _on_fail, {"error": "error", "__next__": "extract_steps"})
    g.add_conditional_edges("extract_steps",   _on_fail, {"error": "error", "__next__": "finalize"})

    # End
    g.add_edge("finalize", END)
    g.add_edge("error",    END)

    return g


_COMPILED_GRAPH = _build_graph().compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    job_id: str,
    input_type: str,
    output_mode: str = "meeting_analysis",
    audio_path: Optional[str] = None,
    raw_text: Optional[str] = None,
) -> None:
    print(f"\n[PIPELINE] job={job_id} | type={input_type} | mode={output_mode}", flush=True)

    initial_state: MeetingState = {
        "job_id":               job_id,
        "input_type":           input_type,
        "output_mode":          output_mode,
        "audio_path":           audio_path,
        "raw_text":             raw_text,
        "transcript":           None,
        "summary":              None,
        "action_items":         None,
        "risks":                None,
        "mom_document":         None,
        "email_draft":          None,
        "detailed_explanation": None,
        "steps_detail":         None,
        "status":               "pending",
        "error":                None,
    }

    try:
        _COMPILED_GRAPH.invoke(initial_state)
        print(f"[PIPELINE] Completed: {job_id}", flush=True)
    except Exception as exc:
        print(f"[PIPELINE] ERROR: {exc}", flush=True)
        traceback.print_exc()
        job_store.update_job(job_id, status="failed", error=f"Pipeline error: {exc}", current_agent="")

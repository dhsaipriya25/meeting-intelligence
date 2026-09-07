"""
LLM client wrapping AWS Bedrock (Amazon Nova Pro).
Uses invoke_model API to avoid URL encoding issues with converse API.
"""

import os
import json
import time
from typing import Callable

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
_REGION   = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

_bedrock_client = None


def _get_client():
    global _bedrock_client
    if _bedrock_client is None:
        access_key    = os.getenv("AWS_ACCESS_KEY_ID", "")
        secret_key    = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        session_token = os.getenv("AWS_SESSION_TOKEN", "")

        if not access_key or not secret_key:
            raise EnvironmentError(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in .env file."
            )

        kwargs = {
            "service_name": "bedrock-runtime",
            "region_name": _REGION,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }
        if session_token:
            kwargs["aws_session_token"] = session_token

        _bedrock_client = boto3.client(**kwargs)
        print(f"[LLM] Bedrock client created | region={_REGION} model={_MODEL_ID}", flush=True)
    return _bedrock_client


def bedrock_generate(
    prompt: str,
    system: str = "",
    model: str = None,
) -> str:
    """
    Send a prompt to AWS Bedrock using invoke_model and return the response text.
    Retries up to 3 times on throttling errors.
    """
    client   = _get_client()
    model_id = model or _MODEL_ID

    # Build request body for Amazon Nova / Claude on Bedrock
    body = {
        "messages": [
            {"role": "user", "content": [{"text": prompt}]}
        ],
        "inferenceConfig": {
            "maxTokens": 4096,
            "temperature": 0.3,
        },
    }
    if system:
        body["system"] = [{"text": system}]

    last_exc = None
    for attempt in range(3):
        try:
            print(f"[LLM] invoke_model model={model_id} attempt={attempt+1}", flush=True)
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())

            # Amazon Nova Pro response format
            text = result["output"]["message"]["content"][0]["text"]
            print(f"[LLM] Response OK ({len(text)} chars)", flush=True)
            return text.strip()

        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            print(f"[LLM] ClientError: {code} — {exc}", flush=True)
            if code in ("ThrottlingException", "ServiceUnavailableException", "ModelNotReadyException"):
                last_exc = exc
                if attempt < 2:
                    print(f"[LLM] Retrying in 5s...", flush=True)
                    time.sleep(5)
            else:
                raise RuntimeError(f"Bedrock error [{code}]: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Bedrock error: {exc}") from exc

    raise RuntimeError(f"Bedrock throttling after 3 attempts: {last_exc}")


# Alias so all agents work without changes
groq_generate = bedrock_generate


def chunk_text(
    text: str,
    chunk_size: int = 8000,
    overlap: int = 300,
) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap

    return chunks


def map_reduce(
    chunks: list[str],
    chunk_prompt_fn: Callable[[str], str],
    reduce_prompt: str,
    system: str = "",
) -> str:
    """Map-reduce over text chunks using Bedrock LLM."""
    partial_results: list[str] = []
    for i, chunk in enumerate(chunks):
        print(f"[LLM] map_reduce chunk {i+1}/{len(chunks)}", flush=True)
        result = bedrock_generate(chunk_prompt_fn(chunk), system=system)
        partial_results.append(f"--- Chunk {i + 1} ---\n{result}")

    combined = "\n\n".join(partial_results)
    final_prompt = (
        f"{reduce_prompt}\n\n"
        f"Partial results from each chunk:\n\n{combined}"
    )
    return bedrock_generate(final_prompt, system=system)

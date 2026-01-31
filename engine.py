import os
import json
from datetime import datetime
from google import genai
from google.genai import types
from .models import Provenance

# Configure Client
# Ensure GEMINI_API_KEY is set in your environment
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

client = genai.Client(api_key=API_KEY)

# 2026 Modern Default: Gemini 2.0 Flash
# Replaces deprecated 'gemini-flash-lite-latest'
DEFAULT_MODEL = "gemini-2.0-flash" 

def _clean_json_text(text: str) -> str:
    """
    Removes Markdown code blocks (```json ... ```) if present.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2:
            cleaned = "\n".join(lines[1:-1])
    return cleaned.strip()

async def call_gemini(
    system_instruction: str,
    user_prompt: str,
    temperature: float = 0.2,
    model_name: str = DEFAULT_MODEL
) -> tuple[dict, Provenance]:
    """
    Executes a Gemini call with the modern google-genai SDK.
    Includes a single 'Self-Repair' loop for JSON validity.
    """
    
    # Configuration for the new SDK
    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_instruction,
        response_mime_type="application/json" # Enforce JSON mode
    )

    # --- Attempt 1 ---
    start_time = datetime.utcnow()
    raw_text = ""
    
    try:
        # Note the usage of .aio for async calls in the new SDK
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=config
        )
        raw_text = response.text
    except Exception as e:
        raise RuntimeError(f"Gemini API failure: {str(e)}")

    data = None
    repair_attempts = 0
    
    try:
        clean_text = _clean_json_text(raw_text)
        data = json.loads(clean_text)
    except json.JSONDecodeError:
        # --- Attempt 2: Self-Repair ---
        repair_attempts = 1
        repair_prompt = (
            f"The following JSON is invalid. Fix the syntax and return ONLY the raw JSON.\n\n"
            f"Broken JSON:\n{raw_text}"
        )
        
        # Repair runs at Temp 0 for determinism
        repair_config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json"
        )
        
        try:
            repair_resp = await client.aio.models.generate_content(
                model=model_name,
                contents=repair_prompt,
                config=repair_config
            )
            repaired_text = _clean_json_text(repair_resp.text)
            data = json.loads(repaired_text)
        except Exception:
             # If repair fails, we bubble up the error to the UI
            raise ValueError(f"Failed to generate valid JSON after repair. Raw output: {raw_text[:100]}...")

    # --- Provenance Construction ---
    provenance = Provenance(
        prompt=f"SYSTEM: {system_instruction}\n\nUSER: {user_prompt}",
        model_name=model_name,
        model_params={"temperature": temperature},
        raw_response=raw_text,
        repair_attempts=repair_attempts,
        timestamp=start_time
    )

    return data, provenance

async def run_baseline_chat(user_prompt: str) -> tuple[str, Provenance]:
    """
    A standard, high-temperature chat call for the Baseline comparison.
    """
    # Baseline uses higher temp and no JSON enforcement
    config = types.GenerateContentConfig(temperature=0.7)
    
    try:
        response = await client.aio.models.generate_content(
            model=DEFAULT_MODEL,
            contents=user_prompt,
            config=config
        )
        raw_text = response.text
    except Exception as e:
        raise RuntimeError(f"Baseline API failure: {str(e)}")
    
    prov = Provenance(
        prompt=user_prompt,
        model_name=DEFAULT_MODEL,
        model_params={"temperature": 0.7, "mode": "baseline"},
        raw_response=raw_text,
        repair_attempts=0
    )
    
    return raw_text, prov

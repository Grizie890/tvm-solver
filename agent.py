"""
agent.py
--------
Orchestrator: receives the user's natural-language question,
calls Claude to extract variables and decide which tvm_tools
function to call, then executes that function deterministically
and returns a formatted answer.

Claude never does the arithmetic — it only routes and extracts.
"""

import json
import re
import anthropic
from tvm_tools import (
    solve_pv,
    solve_fv,
    solve_rate,
    solve_n,
    convert_rate,
    force_of_interest,
    rate_from_force,
    equation_of_value,
)

# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = {
    "solve_pv": solve_pv,
    "solve_fv": solve_fv,
    "solve_rate": solve_rate,
    "solve_n": solve_n,
    "convert_rate": convert_rate,
    "force_of_interest": force_of_interest,
    "rate_from_force": rate_from_force,
    "equation_of_value": equation_of_value,
}

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a Time Value of Money (TVM) assistant for actuarial exam students.
Your ONLY job is to read the user's question, extract the known variables,
and respond with a JSON object that tells the backend which function to call.

Sign convention: cash inflows are POSITIVE, outflows are NEGATIVE.
All rates must be expressed as decimals (e.g. 5% → 0.05).

You must respond with ONLY a JSON object — no prose, no markdown fences.

The JSON must have exactly this shape:
{
  "function": "<one of the function names below>",
  "args": { <keyword arguments for that function> },
  "explanation": "<one sentence plain-English explanation of what you are solving>"
}

Available functions and their required args:

1. solve_pv       — args: fv, pmt, i, n          (omit pmt if not given, default 0)
2. solve_fv       — args: pv, pmt, i, n          (omit pmt if not given, default 0)
3. solve_rate     — args: pv, fv, n
4. solve_n        — args: pv, fv, i
5. convert_rate   — args: nominal_rate, from_compounding, to_compounding
                    (use 0 for continuous compounding)
6. force_of_interest — args: i_effective_annual
7. rate_from_force   — args: delta
8. equation_of_value — args: cashflows (list of {amount, time}), i, valuation_time

If the question is ambiguous or missing required variables, set "function" to
"error" and put a helpful message in "explanation".

Examples:
Q: What is the PV of $5000 in 3 years at 6% annual?
→ {"function":"solve_pv","args":{"fv":5000,"i":0.06,"n":3},"explanation":"Discounting a lump sum of $5000 back 3 years at 6%."}

Q: Convert 12% compounded monthly to an annual effective rate.
→ {"function":"convert_rate","args":{"nominal_rate":0.12,"from_compounding":12,"to_compounding":1},"explanation":"Converting a monthly-compounded nominal rate to an effective annual rate."}
"""

# ── Main entry point ──────────────────────────────────────────────────────────

def run_agent(user_question: str, api_key: str) -> dict:
    """
    Full pipeline:
      1. Send question to Claude → get routing JSON
      2. Parse JSON
      3. Call the deterministic tvm_tools function
      4. Return a response dict for the UI
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Step 1 — ask Claude to route
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_question}],
    )

    raw = message.content[0].text.strip()

    # Step 2 — parse routing JSON
    # Strip any accidental markdown fences just in case
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        routing = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Claude returned an unexpected format. Please rephrase your question.",
            "raw": raw,
        }

    fn_name = routing.get("function")
    args = routing.get("args", {})
    explanation = routing.get("explanation", "")

    if fn_name == "error" or fn_name not in TOOLS:
        return {
            "success": False,
            "error": explanation or f"Unknown function: {fn_name}",
        }

    # Step 3 — call deterministic function
    try:
        calc_result = TOOLS[fn_name](**args)
    except Exception as e:
        return {
            "success": False,
            "error": f"Calculation error: {str(e)}",
        }

    # Step 4 — build response for UI
    return {
        "success": True,
        "explanation": explanation,
        "function_called": fn_name,
        "result": calc_result,
    }

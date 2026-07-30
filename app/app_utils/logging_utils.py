# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import re
from typing import Any

logger = logging.getLogger("nutri_meal_agent")

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def redact_pii(val: Any) -> Any:
    """Recursively redacts sensitive PII (email, phone, SSN) from strings, dicts, and lists."""
    if isinstance(val, str):
        val = EMAIL_REGEX.sub("[REDACTED_EMAIL]", val)
        val = PHONE_REGEX.sub("[REDACTED_PHONE]", val)
        val = SSN_REGEX.sub("[REDACTED_SSN]", val)
        return val
    elif isinstance(val, dict):
        return {k: redact_pii(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [redact_pii(item) for item in val]
    return val


def log_tool_intent(tool_name: str, intent: str, inputs: dict) -> None:
    """Logs the explicit INTENT before a tool executes, with PII redaction."""
    safe_inputs = redact_pii(inputs)
    logger.info(
        f"[TOOL INTENT] [{tool_name}] {intent}",
        extra={
            "event_type": "TOOL_INTENT",
            "tool_name": tool_name,
            "intent_description": intent,
            "inputs": safe_inputs,
        },
    )


def log_tool_outcome(tool_name: str, outcome: str, results: dict, error: Exception | None = None) -> None:
    """Logs the explicit OUTCOME after a tool executes, with PII redaction."""
    safe_results = redact_pii(results)
    if error:
        logger.error(
            f"[TOOL OUTCOME ERROR] [{tool_name}] {outcome} - Error: {error}",
            extra={
                "event_type": "TOOL_OUTCOME_ERROR",
                "tool_name": tool_name,
                "outcome_description": outcome,
                "error_details": str(error),
            },
        )
    else:
        logger.info(
            f"[TOOL OUTCOME] [{tool_name}] {outcome}",
            extra={
                "event_type": "TOOL_OUTCOME_SUCCESS",
                "tool_name": tool_name,
                "outcome_description": outcome,
                "results": safe_results,
            },
        )

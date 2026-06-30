import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def is_valid_text(val) -> bool:
    if not val:
        return False
    val_str = str(val).strip()
    if len(val_str) < 3 or val_str.startswith("{") or val_str.startswith("["):
        return False
    return True

def lambda_handler(event, context):
    logger.info(f"Incoming Event: {json.dumps(event)}")
    evaluation_input = event.get("evaluationInput", {})
    spans = evaluation_input.get("sessionSpans", []) or evaluation_input.get("traceSpans", [])
    
    final_response = evaluation_input.get("finalResponse") or evaluation_input.get("completion")

    # Universal Span Attribute Scan to capture nested message generations
    if not final_response and spans:
        for span in spans:
            attributes = span.get("attributes", {}) or {}
            for key, value in attributes.items():
                key_lower = key.lower()
                if any(x in key_lower for x in ["output", "completion", "response", "message", "generation"]):
                    if isinstance(value, (dict, list)):
                        val_json = json.dumps(value)
                        if "text" in val_json or "content" in val_json:
                            final_response = val_json
                            break
                    elif is_valid_text(value):
                        final_response = str(value)
                        break
            if final_response:
                break

    if not final_response or not str(final_response).strip():
        return {
            "score": 0.0, "value": 0.0, "label": "FAILED",
            "explanation": "Agent evaluation failed: No valid response strings found inside telemetry data blocks."
        }

    clean_text = str(final_response).strip()
    return {
        "score": 1.0, "value": 1.0, "label": "PASSED",
        "explanation": f"Agent successfully produced a valid final response trace (Captured: {clean_text[:40]}...)"
    }

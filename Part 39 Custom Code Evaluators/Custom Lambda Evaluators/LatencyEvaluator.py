import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def parse_to_timestamp(dt_str) -> float:
    if not dt_str:
        return None
    try:
        return float(dt_str)
    except (ValueError, TypeError):
        pass
    try:
        clean_str = str(dt_str).strip()
        dt_obj = datetime.fromisoformat(clean_str)
        return dt_obj.timestamp()
    except Exception as e:
        logger.error(f"Failed to parse datetime string '{dt_str}': {str(e)}")
        return None

def lambda_handler(event, context):
    logger.info(f"Incoming Event: {json.dumps(event)}")
    evaluation_input = event.get("evaluationInput", {})
    spans = evaluation_input.get("sessionSpans", []) or evaluation_input.get("traceSpans", [])
    
    if not spans:
        return {
            "label": "FAILED", "score": 0.0, "value": 0.0,
            "explanation": "No OpenTelemetry spans discovered in evaluationInput."
        }

    # Group timestamps by native OpenTelemetry trace groups
    trace_groups = {}
    for span in spans:
        span_trace_id = span.get("traceId") or span.get("trace_id")
        if not span_trace_id:
            continue
            
        s_time_parsed = parse_to_timestamp(span.get("startTime") or span.get("start_time"))
        e_time_parsed = parse_to_timestamp(span.get("endTime") or span.get("end_time"))
        
        if span_trace_id not in trace_groups:
            trace_groups[span_trace_id] = {"starts": [], "ends": []}
        if s_time_parsed is not None:
            trace_groups[span_trace_id]["starts"].append(s_time_parsed)
        if e_time_parsed is not None:
            trace_groups[span_trace_id]["ends"].append(e_time_parsed)

    durations = []
    for t_id, times in trace_groups.items():
        if times["starts"] and times["ends"]:
            durations.append(max(times["ends"]) - min(times["starts"]))

    if not durations:
        return {
            "label": "FAILED", "score": 0.0, "value": 0.0,
            "explanation": "Could not extract processing durations from session telemetry."
        }

    # Calculate mean turn latency for the batch execution sequence
    total_latency = sum(durations) / len(durations)

    # Performance evaluation tiers for multi-LLM workflows
    if total_latency < 4.0:
        score, label, msg = 1.0, "PASSED", "Excellent average performance across the multi-LLM batch."
    elif total_latency < 9.5:
        score, label, msg = 0.75, "PASSED", "Standard batch performance within normal execution bounds."
    elif total_latency < 12.0:
        score, label, msg = 0.50, "FAILED", "Slightly degraded execution baseline."
    else:
        score, label, msg = 0.0, "FAILED", "Critical latency bottleneck detected."

    return {
        "score": score,
        "value": round(total_latency, 4),
        "label": label,
        "explanation": f"Workflow batch completed with an average of {total_latency:.2f} seconds per turn. {msg}"
    }

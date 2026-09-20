"""
Human-in-the-Loop (HITL) generic context formatter and metadata helpers.
Operates dynamically on tool manifests and JSON Schema descriptors without hardcoded tool conditionals.
"""
import re
from typing import Any, Dict, Optional


def _humanize_key(key: str) -> str:
    """Transform snake_case identifiers into human-readable Title Case labels."""
    if not key:
        return ""
    if key.lower() == "pid":
        return "PID"
    if key.lower() == "url":
        return "URL"
    return key.replace("_", " ").title()


def _safe_format_template(template: str, arguments: Dict[str, Any]) -> str:
    """
    Interpolate named argument placeholders into a template string safely without raising KeyError.
    Example: '{nombre_proceso}' with arguments={'nombre_proceso': 'calc.exe'} -> 'calc.exe'.
    """
    def replacer(match: re.Match) -> str:
        placeholder = match.group(1)
        val = arguments.get(placeholder)
        if val is not None and str(val).strip():
            return str(val)
        return ""

    formatted = re.sub(r"\{([a-zA-Z0-9_]+)\}", replacer, template)
    # Clean up redundant spaces if missing placeholders were stripped
    return re.sub(r"\s+", " ", formatted).strip()


def generate_confirmation_context(
    tool_name: str,
    arguments: Dict[str, Any],
    tool_def: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construct dynamic, structured human-readable context for any critical tool execution.

    Extracts presentation metadata directly from the tool's descriptor and argument dictionary,
    enforcing the Open-Closed Principle (OCP) with zero hardcoded tool name conditionals.

    Args:
        tool_name: Identifier of the tool requesting authorization.
        arguments: Key-value parameters passed by the LLM.
        tool_def: Optional tool schema dictionary received from dynamic discovery.

    Returns:
        A structured dictionary containing title, message, severity, target, and details.
    """
    humanized_name = _humanize_key(tool_name)
    title = f"Autorización: {humanized_name}"

    # 1. Resolve confirmation message dynamically
    confirmation_template = (
        tool_def.get("confirmation_template") if tool_def else None
    )

    if confirmation_template:
        message = _safe_format_template(confirmation_template, arguments)
    else:
        message = f"¿Desea autorizar la ejecución de '{humanized_name}' con los parámetros indicados?"

    # 2. Determine primary target identifier from arguments dynamically
    target_val = None
    for key, val in arguments.items():
        if val is not None and str(val).strip():
            target_val = str(val)
            break

    target_str = target_val if target_val else humanized_name

    # 3. Format structured argument details generically
    details: Dict[str, str] = {}
    for key, val in arguments.items():
        label = _humanize_key(key)
        details[label] = str(val) if val is not None else "N/A"

    return {
        "title": title,
        "message": message,
        "severity": "CRITICAL",
        "target": target_str,
        "details": details,
    }


__all__ = ["generate_confirmation_context"]

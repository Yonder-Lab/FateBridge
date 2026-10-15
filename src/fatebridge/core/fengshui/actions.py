"""Filter sourced actions by explicit permissions; never invent physical facts."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .models import LayoutConstraint


def permission_state(
    constraint: Optional["LayoutConstraint"], routes: List[List[str]]
) -> str:
    """Routes are alternatives; operations within each route are conjunctive."""
    states = []
    for route in routes:
        values = [
            (
                getattr(
                    constraint,
                    {
                        "location": "can_relocate",
                        "facing": "can_rotate",
                        "add_items": "can_add_items",
                    }[operation],
                )
                if constraint is not None
                else None
            )
            for operation in route
        ]
        states.append(
            "blocked"
            if False in values
            else "allowed" if all(v is True for v in values) else "unknown"
        )
    return (
        "allowed"
        if "allowed" in states
        else "unknown" if "unknown" in states else "blocked"
    )


def apply_permission(
    action: Dict[str, Any],
    constraint: Optional["LayoutConstraint"],
    routes: List[List[str]],
    *,
    status_key: str = "action_status",
) -> None:
    if constraint is None:
        return
    state = permission_state(constraint, routes)
    action["permission_status"] = state
    action["constraint_evidence"] = constraint.evidence
    if state == "blocked":
        action[status_key] = "blocked"
        action["pending_confirmations"] = []
        action["blocked_reason"] = "explicit_action_constraint"


FORM_ACTION_ROUTES = {
    "entrance_visible": [["location"], ["facing"]],
    "entrance_direct_line": [["location"]],
    "solid_backing": [["location"], ["add_items"]],
    "passage_direct_line": [["location"]],
    "exposed_beam_over_user": [["location"]],
    "window_to_side": [["location"], ["facing"]],
}

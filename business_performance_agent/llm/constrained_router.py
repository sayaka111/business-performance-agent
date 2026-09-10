from ..models.schemas import BoundaryError


class ConstrainedRouter:
    def __init__(self, client=None):
        self.client = client

    def choose(self, allowed_candidates, context, node):
        if len(allowed_candidates) < 2:
            raise ValueError("LLM must not be called for zero/one candidate")
        if self.client is None:
            return {
                "choice": "no_valid_choice",
                "rationale": "llm_provider_not_configured",
                "mode": "agentic_router_interface",
            }
        response = self.client.structured_generate(
            purpose="routing",
            payload={
                "allowed_candidates": allowed_candidates,
                "context": context,
                "node": node,
            },
            schema={
                "type": "object",
                "required": ["choice", "rationale"],
                "properties": {
                    "choice": {"enum": allowed_candidates + ["no_valid_choice"]},
                    "rationale": {"type": "string"},
                },
            },
        )
        if not isinstance(response, dict) or response.get(
            "choice"
        ) not in allowed_candidates + ["no_valid_choice"]:
            raise BoundaryError(
                "evidence_boundary_reached",
                "Router returned a choice outside allowed_candidates.",
            )
        return dict(
            choice=response["choice"],
            rationale=str(response.get("rationale", ""))[:500],
            mode="agentic_router_interface",
        )

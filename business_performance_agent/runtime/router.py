from ..tools.calculations import coverage


class Router:
    def __init__(self, definition, constrained):
        self.rules = definition["routing_rules"]["routing_rules"]
        self.policy = definition["policy"]["diagnosis_policy"]
        self.constrained = constrained

    def rule(self, node, condition):
        return next(
            r for r in self.rules if r["from"] == node and r["condition"] == condition
        )

    def stop(self, state, *, lateral=False):
        if state.depth >= self.policy["max_depth"]:
            return "max_depth_reached"
        if (
            state.selected_driver
            and state.selected_driver["aligned_share"]
            < self.policy["branch_min_contribution"]
        ):
            return "below_min_contribution"
        if lateral and state.aligned_coverage >= self.policy["target_aligned_coverage"]:
            return "target_coverage_reached"
        return None

    def select(self, candidates, context, node, trace):
        requested = context.get("preferred_dimension")
        explicit = (
            requested
            if requested in candidates
            else "dimension:" + requested
            if isinstance(requested, str) and "dimension:" + requested in candidates
            else None
        )
        if explicit:
            decision = {
                "choice": explicit,
                "rationale": "explicit_legal_dimension",
                "mode": "deterministic",
            }
        elif len(candidates) == 1:
            decision = {
                "choice": candidates[0],
                "rationale": "unique_valid_candidate",
                "mode": "deterministic",
            }
        elif not candidates:
            decision = {
                "choice": "no_valid_choice",
                "rationale": "empty_candidate_set",
                "mode": "deterministic",
            }
        else:
            decision = self.constrained.choose(candidates, context, node)
        trace["router_decisions"].append(
            dict(node=node, allowed_candidates=candidates, **decision)
        )
        return decision["choice"]

    def significant(self, contribution):
        aligned = [x for x in contribution["effects"] if x["role"] == "aligned_driver"]
        primary = aligned[0] if aligned else None
        secondary = [
            x
            for x in aligned[1:]
            if x["aligned_share"]
            >= self.policy["retain_secondary_driver_if_contribution_gte"]
        ]
        return primary, secondary, coverage(([primary] if primary else []) + secondary)

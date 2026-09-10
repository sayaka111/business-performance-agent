from dataclasses import asdict
from uuid import uuid4
import json
import os
from .state import WorkflowState
from .executor import Executor
from .router import Router
from ..models.schemas import WorkflowInput, BoundaryError
from ..llm.constrained_router import ConstrainedRouter
from ..llm.result_builder import build_result, candidate_claims


class Runtime:
    """One explicit node per iteration; state and each transition are persisted."""

    def __init__(self, knowledge, query, definition, settings, llm_client=None):
        self.knowledge, self.query, self.definition, self.settings = (
            knowledge,
            query,
            definition,
            settings,
        )
        self.llm_client = llm_client
        self.router = Router(definition, ConstrainedRouter(llm_client))

    def run(self, raw):
        s = self.state = WorkflowState()
        self.trace = {
            "run_id": str(uuid4()),
            "workflow_id": self.definition["workflow_id"],
            "workflow_version": self.definition["workflow_version"],
            "input": raw,
            "nodes_executed": [],
            "skills_called": [],
            "router_decisions": [],
            "state_snapshots": [],
            "spec_fingerprints": dict(
                self.knowledge.fingerprints, **self.definition["fingerprints"]
            ),
        }
        self.executor = Executor(
            self.knowledge,
            self.query,
            s,
            self.trace,
            self.definition["policy"]["execution_policy"],
        )
        self.target, self.primary, self.secondary, self.claims = {}, None, [], []
        self.input = None
        self.pending = None
        self.visited = set()
        self.first_level = True
        self.contribution_mode = "relationship"
        self.final_result = None
        while s.current_node != "complete":
            node = s.current_node
            self.trace["nodes_executed"].append(node)
            try:
                next_node = getattr(self, "node_" + node)()
            except BoundaryError as exc:
                s.limitations.append(exc.detail)
                next_node = self.fail(exc.reason)
            except Exception as exc:
                s.limitations.append(f"{type(exc).__name__}: {exc}")
                if node == "build_result":
                    s.workflow_status = "failed"
                    s.stop_reason = "execution_failure"
                    self.save_trace()
                    raise RuntimeError(
                        "Output contract validation failed; trace saved, no unvalidated result published."
                    ) from exc
                next_node = self.fail("execution_failure")
            self.trace["router_decisions"].append(
                {
                    "from": node,
                    "to": next_node,
                    "mode": "deterministic",
                    "rationale": "workflow_node_result",
                }
            )
            s.current_node = next_node
            self.trace["state_snapshots"].append(
                s.validate(self.definition["state_schema"])
            )
            self.save_trace()
        self.trace["nodes_executed"].append("complete")
        if self.final_result is None:
            self.final_result = build_result(
                self.definition,
                s,
                self.target,
                self.primary,
                self.secondary,
                self.claims,
            )
        self.save_trace()
        return dict(
            run_id=self.trace["run_id"],
            result=self.final_result,
            trace_path=str(self.trace_path),
        )

    def save_trace(self):
        s = self.state
        self.trace.update(
            warnings=s.warnings,
            limitations=s.limitations,
            evidence=s.evidence,
            stop_reason=s.stop_reason,
            final_structured_result=self.final_result,
            state=asdict(s),
        )
        if hasattr(self.query.adapter, "operations"):
            self.trace["data_source"] = {
                "backend": "SQLite",
                "dataset_id": self.query.adapter.mapping["dataset_id"],
                "database": str(self.query.adapter.path),
                "production_database": False,
                "database_sha256": self.query.adapter.fingerprint,
            }
            self.trace["query_operations"] = self.query.adapter.operations
            self.trace["semantic_queries"] = self.query.calls
        if hasattr(self.llm_client, "events"):
            self.trace["llm_events"] = self.llm_client.events
        self.settings.logs.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.settings.logs / (self.trace["run_id"] + ".json")
        temporary = self.trace_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.trace, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        os.replace(temporary, self.trace_path)

    def route(self, node, condition):
        return self.router.rule(node, condition)["to"]

    def scope(self, metric=None):
        return dict(
            metric_id=metric or self.state.current_metric,
            current_period=asdict(self.input.current_period),
            baseline_period=asdict(self.input.baseline_period),
            filters=dict(self.state.current_filters),
        )

    def quality(self, metrics, dimensions=None):
        return self.executor.call(
            "data_quality_guard",
            analysis_scope=dict(
                metrics=metrics,
                dimensions=dimensions or [],
                current_period=asdict(self.input.current_period),
                baseline_period=asdict(self.input.baseline_period),
                filters=dict(self.state.current_filters),
            ),
        )

    def record(self, kind, fact, level, *, scope=None, provenance=None):
        eid = f"E{len(self.state.evidence) + 1:04d}"
        self.state.evidence.append(
            dict(
                evidence_id=eid,
                evidence_level=level,
                source_step=self.state.current_node,
                payload=dict(
                    kind=kind,
                    fact=fact,
                    scope=scope or self.scope(),
                    provenance=provenance or [],
                ),
            )
        )

    def fail(self, reason, result=None):
        s = self.state
        legal = self.definition["state_schema"]["state"]["stop_reason"]["enum"]
        s.stop_reason = reason if reason in legal else "evidence_boundary_reached"
        s.failed_branches.append(
            dict(
                node=s.current_node,
                metric_id=s.current_metric,
                filters=dict(s.current_filters),
                reason=reason,
            )
        )
        s.limitations.append(f"Analysis stopped at {s.current_node}: {reason}.")
        if reason in ("semantic_conflict", "data_quality_boundary", "invalid_input"):
            s.workflow_status = "blocked"
        elif (
            s.evidence
            and self.definition["policy"]["execution_policy"][
                "allow_partial_completion"
            ]
        ):
            s.workflow_status = "partial"
        else:
            s.workflow_status = "failed" if reason == "execution_failure" else "blocked"
        return (
            "build_result"
            if s.current_node in ("evidence_validate", "build_result")
            else "evidence_validate"
        )

    def check(self, result):
        return (
            self.fail(result.reason or "execution_failure")
            if result.status in ("blocked", "failed")
            else None
        )

    def stop(self, reason):
        self.state.stop_reason = reason
        self.state.workflow_status = "completed"
        return "evidence_validate"

    def node_validate_input(self):
        try:
            self.input = WorkflowInput.parse(
                self.trace["input"], self.knowledge, self.definition
            )
        except (KeyError, ValueError, TypeError, BoundaryError):
            return self.route("validate_input", "input_valid == false")
        s = self.state
        s.workflow_status = "running"
        s.target_metric = s.current_metric = self.input.metric_id
        s.current_period, s.baseline_period = (
            asdict(self.input.current_period),
            asdict(self.input.baseline_period),
        )
        s.current_filters = dict(self.input.filters)
        return self.route("validate_input", "input_valid == true")

    def node_terminate_invalid_input(self):
        return self.fail("invalid_input")

    def node_terminate_blocked(self):
        return self.fail(self.pending.reason or "data_quality_boundary")

    def node_data_quality_guard(self):
        dimensions = list(self.state.current_filters)
        requested = self.input.context.get("preferred_dimension")
        if requested and not self.query.dimension_available(requested):
            dimensions.append(requested)
        self.pending = self.quality([self.state.target_metric], dimensions)
        if self.pending.status == "failed":
            return self.check(self.pending)
        return self.route(
            "data_quality_guard",
            "analysis_allowed == "
            + str(self.pending.result.get("analysis_allowed", False)).lower(),
        )

    def node_metric_compare(self):
        result = self.executor.call("metric_compare", **self.scope())
        if failure := self.check(result):
            return failure
        self.target = result.result
        self.record(
            "comparison", self.target, "direct", provenance=self.target["provenance"]
        )
        return "anomaly_evaluate"  # workflow.md Step 3 -> Step 4

    def node_anomaly_evaluate(self):
        result = self.executor.call(
            "anomaly_evaluate",
            metric_compare_result=self.target,
            anomaly_policy=self.definition["policy"]["anomaly_policy"],
        )
        if failure := self.check(result):
            return failure
        self.record("anomaly", result.result, "derived")
        return self.route(
            "anomaly_evaluate",
            "is_anomaly == " + str(result.result["is_anomaly"]).lower(),
        )

    def node_complete_no_anomaly(self):
        self.state.workflow_status = "completed_no_anomaly"
        self.state.stop_reason = "not_anomaly"
        return "evidence_validate"

    def node_decompose_gross_gmv(self):
        self.state.selected_relationship = self.router.rule(
            "decompose_gross_gmv", "always"
        )["forced_relationship"]
        return self.decompose()

    def decompose(self):
        s = self.state
        relationship = self.knowledge.get_relationship(s.selected_relationship)
        metrics = relationship.get(
            "drivers", [x["metric"] for x in relationship.get("components", [])]
        )
        if not self.query.relationship_available(relationship):
            return self.fail("data_unavailable")
        quality = self.quality([s.current_metric] + metrics, list(s.current_filters))
        if failure := self.check(quality):
            return failure
        result = self.executor.call(
            "metric_decompose", **self.scope(), relationship_id=s.selected_relationship
        )
        if failure := self.check(result):
            return failure
        s.decomposition_result = result.result
        self.record(
            "decomposition",
            result.result,
            "direct",
            provenance=result.result["provenance"],
        )
        s.depth += 1
        s.analysis_path.append(
            dict(
                node_type="decomposition",
                metric_id=s.current_metric,
                relationship_id=s.selected_relationship,
                dimension_id=None,
                segment_id=None,
            )
        )
        self.visited.add(
            (
                s.current_metric,
                s.selected_relationship,
                tuple(sorted(s.current_filters.items())),
            )
        )
        self.contribution_mode = "relationship"
        return "contribution_analysis"

    def node_metric_decompose(self):
        return self.decompose()

    def node_decompose_aov(self):
        return self.decompose()

    def node_contribution_analysis(self):
        s = self.state
        comparison = self.executor.call("metric_compare", **self.scope())
        if failure := self.check(comparison):
            return failure
        if self.contribution_mode == "relationship":
            parts = s.decomposition_result["drivers"]
            identifiers = dict(relationship_id=s.selected_relationship)
        else:
            parts = self.pending.result["segments"]
            identifiers = dict(dimension_id=s.selected_dimension)
        result = self.executor.call(
            "contribution_analysis",
            target_metric=s.current_metric,
            target_baseline=comparison.result["baseline_value"],
            target_current=comparison.result["current_value"],
            components=parts,
            **identifiers,
        )
        if failure := self.check(result):
            return failure
        s.contribution_result = result.result
        self.record(
            "contribution",
            result.result,
            "derived",
            provenance=comparison.result["provenance"],
        )
        s.selected_driver, secondary, s.aligned_coverage = self.router.significant(
            result.result
        )
        if self.first_level:
            self.primary, self.secondary = s.selected_driver, secondary
            self.first_level = False
            return self.route("contribution_analysis", "first_level_gmv_decomposition")
        return (
            "evaluate_stop_policy"
            if self.contribution_mode == "dimension"
            else "evaluate_branch"
        )

    def node_select_primary_driver(self):
        s = self.state
        if reason := self.router.stop(s):
            return self.stop(reason)
        if not s.selected_driver:
            return self.stop("evidence_boundary_reached")
        # A requested dimension concerns the input metric. Preserve the mandatory
        # GMV decomposition/primary first, then localize before changing scope.
        requested = self.input.context.get("preferred_dimension")
        if requested and requested in self.dimensions():
            s.selected_relationship = None
            return "select_next_dimension"
        s.current_metric = s.selected_driver["id"]
        rule = self.router.rule(
            "select_primary_driver", f"selected_driver == '{s.current_metric}'"
        )
        if "forced_relationship" in rule:
            s.selected_relationship = rule["forced_relationship"]
        return rule["to"]

    def node_select_orders_relationship(self):
        s = self.state
        branch = next(
            r for r in self.router.rules if r.get("to") == "select_orders_relationship"
        )
        legal = [
            rid
            for rid in branch["allowed_relationships"]
            if self.query.relationship_available(self.knowledge.get_relationship(rid))
        ]
        s.available_relationships = legal
        context = self.input.context
        conditions = []
        if context.get("customer_structure"):
            conditions.append("user_or_parent_context_requests_customer_structure")
        if context.get("traffic_view"):
            conditions.append("session_data_available_and_traffic_view_relevant")
        if not conditions:
            chosen = self.router.rule(
                "select_orders_relationship", "no_specific_context"
            )["preferred_relationship"]
            if chosen not in legal:
                return self.fail("data_unavailable")
            self.trace["router_decisions"].append(
                dict(
                    node=s.current_node,
                    allowed_candidates=legal,
                    choice=chosen,
                    mode="deterministic",
                    rationale="workflow_default",
                )
            )
        else:
            preferred = [
                self.router.rule("select_orders_relationship", c)[
                    "preferred_relationship"
                ]
                for c in conditions
            ]
            candidates = [x for x in preferred if x in legal]
            if not candidates:
                return self.fail("data_unavailable")
            chosen = self.router.select(candidates, context, s.current_node, self.trace)
        if chosen == "no_valid_choice":
            return self.stop("evidence_boundary_reached")
        s.selected_relationship = chosen
        return "metric_decompose"

    def dimensions(self):
        s = self.state
        return [
            d["id"]
            for d in self.knowledge.all("dimensions")
            if (
                d.get("contribution_support", {}).get(s.current_metric)
                or d.get("descriptive_support", {}).get(s.current_metric)
            )
            and d["id"] not in s.current_filters
            and (s.current_metric, d["id"], tuple(sorted(s.current_filters.items())))
            not in self.visited
            and self.query.dimension_available(d["id"])
        ]

    def node_evaluate_branch(self):
        s = self.state
        if reason := self.router.stop(s):
            return self.stop(reason)
        if not s.selected_driver:
            return self.stop("evidence_boundary_reached")
        # Nested mathematical attribution does not localize the parent metric.
        # Prefer one legal partition at its native grain before switching to a
        # child with a different grain (which can invalidate the dimension).
        if self.native_dimensions(self.dimensions()):
            s.selected_relationship = None
            return "select_next_dimension"
        s.current_metric = s.selected_driver["id"]
        s.selected_relationship = None
        if not self.dimensions():
            return self.stop("no_valid_dimension")
        return self.route(
            "evaluate_branch",
            "stop_condition_met == false and valid_dimension_exists == true",
        )

    def native_dimensions(self, candidates):
        metric = self.state.current_metric
        grain = self.knowledge.get_metric(metric).get("grain")
        return [
            identifier
            for identifier in candidates
            if self.knowledge.get_dimension(identifier).get("assignment_grain") == grain
            and self.knowledge.get_dimension(identifier)
            .get("contribution_support", {})
            .get(metric)
            is True
        ]

    def node_select_next_dimension(self):
        candidates = self.dimensions()
        if not candidates:
            return self.stop("no_valid_dimension")
        requested = self.input.context.get("preferred_dimension")
        if requested not in candidates:
            native = self.native_dimensions(candidates)
            if native:
                self.trace["router_decisions"].append(
                    dict(
                        node=self.state.current_node,
                        metric_id=self.state.current_metric,
                        legal_dimensions=candidates,
                        retained_dimensions=native,
                        mode="deterministic",
                        rationale="prefer_supported_partition_at_metric_grain",
                    )
                )
                candidates = native
        chosen = self.router.select(
            candidates, self.input.context, self.state.current_node, self.trace
        )
        if chosen == "no_valid_choice":
            return self.stop("evidence_boundary_reached")
        self.state.selected_dimension = chosen
        return self.route("select_next_dimension", "dimension_selected")

    def node_dimension_drilldown(self):
        s = self.state
        quality = self.quality(
            [s.current_metric], list(s.current_filters) + [s.selected_dimension]
        )
        if failure := self.check(quality):
            return failure
        self.pending = self.executor.call(
            "dimension_drilldown", **self.scope(), dimension_id=s.selected_dimension
        )
        if failure := self.check(self.pending):
            return failure
        self.record(
            "segments",
            self.pending.result,
            "direct",
            provenance=self.pending.result["provenance"],
        )
        self.visited.add(
            (
                s.current_metric,
                s.selected_dimension,
                tuple(sorted(s.current_filters.items())),
            )
        )
        s.depth += 1
        s.analysis_path.append(
            dict(
                node_type="dimension",
                metric_id=s.current_metric,
                relationship_id=None,
                dimension_id=s.selected_dimension,
                segment_id=None,
            )
        )
        self.contribution_mode = "dimension"
        return self.route(
            "dimension_drilldown",
            "contribution_supported == "
            + str(self.pending.result["contribution_supported"]).lower(),
        )

    def node_evaluate_stop_policy(self):
        s = self.state
        if (
            self.pending.result.get("contribution_supported")
            and s.selected_driver
            and self.definition["policy"]["evidence_policy"][
                "stop_at_external_causal_boundary"
            ]
        ):
            s.limitations.append(
                f"当前证据仅定位到 {s.current_metric} 在 {s.selected_dimension} 的 "
                f"{s.selected_driver['id']} 内部贡献；无法据此判断其变化的进一步外部原因，"
                "贡献归因不证明因果关系。"
            )
        if reason := self.router.stop(s, lateral=True):
            return self.stop(reason)
        if self.pending.result.get("contribution_supported") and s.selected_driver:
            s.current_filters[s.selected_dimension] = s.selected_driver["id"]
            s.analysis_path[-1]["segment_id"] = s.selected_driver["id"]
        return self.route("evaluate_stop_policy", "continue_analysis == true")

    def node_select_next_relationship_or_dimension(self):
        s = self.state
        relationships = [
            r["id"]
            for r in self.knowledge.get_metric_relationships(s.current_metric)
            if self.query.relationship_available(r)
            and (s.current_metric, r["id"], tuple(sorted(s.current_filters.items())))
            not in self.visited
        ]
        s.available_relationships = relationships
        candidates = ["relationship:" + x for x in relationships] + [
            "dimension:" + x for x in self.dimensions()
        ]
        if not candidates:
            return self.stop(
                "no_valid_relationship" if not relationships else "no_valid_dimension"
            )
        chosen = self.router.select(
            candidates, self.input.context, s.current_node, self.trace
        )
        if chosen == "no_valid_choice":
            return self.stop("evidence_boundary_reached")
        kind, identifier = chosen.split(":", 1)
        if kind == "relationship":
            s.selected_relationship = identifier
            return "metric_decompose"
        s.selected_dimension = identifier
        return "dimension_drilldown"

    def node_evidence_validate(self):
        self.claims = []
        for claim in candidate_claims(self.state.evidence):
            result = self.executor.call(
                "evidence_validate", claim=claim, evidence=self.state.evidence
            )
            if (
                result.status in ("success", "warning")
                and result.result["claim_status"] == "supported"
            ):
                self.claims.append(dict(claim, **result.result))
            else:
                self.state.limitations.append("Unsupported core claim removed.")
        return self.route("evidence_validate", "core_claims_validated")

    def node_build_result(self):
        if self.state.workflow_status == "running":
            self.state.workflow_status = "completed"
        self.final_result = build_result(
            self.definition,
            self.state,
            self.target,
            self.primary,
            self.secondary,
            self.claims,
        )
        return self.route("build_result", "always")

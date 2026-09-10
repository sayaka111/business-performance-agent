"""Deterministic numerical operations; no metric definitions here."""

import ast
import math


def absolute_change(current, baseline):
    return None if current is None or baseline is None else current - baseline


def relative_change(current, baseline):
    delta = absolute_change(current, baseline)
    return None if delta is None or baseline == 0 else delta / baseline


def symmetric_two_factor_decomposition(a0, a1, b0, b1):
    return ((a1 - a0) * (b0 + b1) / 2, (b1 - b0) * (a0 + a1) / 2)


def additive_contribution(baseline, current, coefficient=1):
    return coefficient * (current - baseline)


def closure_check(target, effects, *, tolerance=1e-9):
    error = math.fsum(effects) - target
    return {
        "closure_error": error,
        "closed": abs(error) <= tolerance * max(1, abs(target)),
    }


def direction_aligned_effect(change, effect):
    return (
        "aligned_driver"
        if change * effect > 0
        else "offset"
        if change * effect < 0
        else "neutral"
    )


def rank_effects(change, effects):
    aligned_total = math.fsum(
        abs(x["effect"]) for x in effects if change * x["effect"] > 0
    )
    enriched = [
        dict(
            x,
            role=direction_aligned_effect(change, x["effect"]),
            aligned_share=(
                abs(x["effect"]) / aligned_total
                if aligned_total and change * x["effect"] > 0
                else 0.0
            ),
        )
        for x in effects
    ]
    return sorted(
        enriched,
        key=lambda x: (x["role"] != "aligned_driver", -abs(x["effect"]), x["id"]),
    )


def coverage(effects):
    return min(
        1.0,
        math.fsum(x["aligned_share"] for x in effects if x["role"] == "aligned_driver"),
    )


def evaluate_formula(formula, resolve):
    """Interpret only arithmetic syntax from frozen Knowledge, never eval()."""

    def walk(node):
        if isinstance(node, ast.Name):
            return resolve(node.id)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if left is None or right is None:
                return None
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return None if right == 0 else left / right
        raise ValueError("unsupported Knowledge formula syntax")

    return walk(ast.parse(formula, mode="eval").body)

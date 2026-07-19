from __future__ import annotations

from dataclasses import dataclass

from coding_agent.agents.specs import SUBAGENT_SPECS, SubagentSpec


IMPLEMENTATION_KEYWORDS = (
    "agrega",
    "agregar",
    "arregla",
    "arreglar",
    "cambia",
    "cambiar",
    "crea",
    "crear",
    "edita",
    "editar",
    "hacerlo",
    "implementa",
    "implementar",
    "mejora",
    "mejorar",
    "refactor",
    "write",
    "fix",
    "change",
    "implement",
)

VALIDATION_KEYWORDS = (
    "build",
    "check",
    "lint",
    "probar",
    "test",
    "tests",
    "validar",
    "verificar",
)

REVIEW_KEYWORDS = (
    "review",
    "revisar",
    "revisa",
    "diff",
)

RESEARCH_KEYWORDS = (
    "api",
    "arquitectura",
    "buscar",
    "documentacion",
    "docs",
    "framework",
    "harness",
    "investiga",
    "investigar",
    "libreria",
    "pipeline",
    "rag",
    "ruteo",
    "subagente",
    "web",
)

REPO_CONTEXT_KEYWORDS = (
    "agente",
    "archivo",
    "codigo",
    "code",
    "harness",
    "modulo",
    "pipeline",
    "proyecto",
    "repo",
    "repository",
    "subagente",
    "tool",
)


@dataclass(frozen=True)
class RoutedSubagent:
    spec: SubagentSpec
    reason: str


@dataclass(frozen=True)
class SkippedSubagent:
    name: str
    reason: str


@dataclass(frozen=True)
class RoutePlan:
    selected: tuple[RoutedSubagent, ...]
    skipped: tuple[SkippedSubagent, ...]

    @property
    def specs(self) -> list[SubagentSpec]:
        return [entry.spec for entry in self.selected]

    @property
    def selected_names(self) -> list[str]:
        return [entry.spec.name for entry in self.selected]

    def reason_for(self, subagent_name: str) -> str:
        for entry in self.selected:
            if entry.spec.name == subagent_name:
                return entry.reason

        return ""


class SubagentRouter:
    """Selects only the subagents that are useful for the current request."""

    def route(self, request: str) -> RoutePlan:
        normalized = request.lower()
        needs_implementation = contains_any(normalized, IMPLEMENTATION_KEYWORDS)
        needs_validation = contains_any(normalized, VALIDATION_KEYWORDS)
        needs_review = contains_any(normalized, REVIEW_KEYWORDS)
        needs_research = contains_any(normalized, RESEARCH_KEYWORDS)
        needs_repo_context = (
            needs_implementation
            or needs_validation
            or needs_review
            or contains_any(normalized, REPO_CONTEXT_KEYWORDS)
        )

        selected: dict[str, str] = {}

        if needs_repo_context:
            selected["explorer"] = (
                "the request needs repository context or implementation evidence"
            )

        if needs_research:
            selected["researcher"] = (
                "the request asks for technical research, RAG, memory, or web evidence"
            )

        if needs_implementation:
            selected["implementer"] = "the request asks for concrete code changes"
            selected["tester"] = "implementation work should be validated after writes"
            selected["reviewer"] = (
                "implementation work should be reviewed against the request"
            )
        elif needs_validation:
            selected["tester"] = "the request asks for validation or checks"
            selected["reviewer"] = "validation output should be reviewed against the request"
        elif needs_review:
            selected["reviewer"] = "the request asks for review or diff analysis"
        elif not selected:
            selected["researcher"] = "default path for informational requests"

        return RoutePlan(
            selected=tuple(
                RoutedSubagent(
                    spec=SUBAGENT_SPECS[name],
                    reason=reason,
                )
                for name, reason in selected.items()
            ),
            skipped=tuple(
                SkippedSubagent(
                    name=name,
                    reason=skip_reason_for(name),
                )
                for name in SUBAGENT_SPECS
                if name not in selected
            ),
        )


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def skip_reason_for(name: str) -> str:
    reasons = {
        "explorer": "no repository context signal was detected",
        "researcher": "no technical research, RAG, memory, or web signal was detected",
        "implementer": "the request does not ask for code changes",
        "tester": "no validation request and no implementation path was selected",
        "reviewer": (
            "no review request and no implementation or validation path was selected"
        ),
    }
    return reasons.get(name, "subagent was not useful for this request")


def format_route_plan(plan: RoutePlan) -> str:
    selected = ", ".join(
        f"{entry.spec.name} ({entry.reason})"
        for entry in plan.selected
    )
    skipped = ", ".join(
        f"{entry.name} ({entry.reason})"
        for entry in plan.skipped
    )

    return (
        f"Subagent route selected: {selected or 'none'}. "
        f"Skipped: {skipped or 'none'}."
    )

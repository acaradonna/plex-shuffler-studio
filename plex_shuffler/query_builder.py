"""Query builder domain model with parse/serialize helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode

from plex_shuffler.query_catalog import known_field_keys

QueryMode = Literal["builder", "advanced"]
ClauseOp = Literal["eq", "contains", "gte", "lte", "exists", "custom"]

DEFAULT_KNOWN_FIELDS = known_field_keys()

_ALLOWED_OPS: set[str] = {"eq", "contains", "gte", "lte", "exists", "custom"}


@dataclass
class Clause:
    field: str
    op: ClauseOp = "eq"
    values: list[str] = field(default_factory=list)


@dataclass
class Group:
    clauses: list[Clause] = field(default_factory=list)


@dataclass
class QueryState:
    mode: QueryMode = "builder"
    groups: list[Group] = field(default_factory=list)
    advanced_query: str = ""


def parse_query_string(
    query: str,
    *,
    known_fields: set[str] | None = None,
    strict: bool = False,
) -> QueryState:
    trimmed = (query or "").strip()
    if not trimmed:
        return QueryState(mode="builder", groups=[], advanced_query="")

    pairs = parse_qsl(trimmed, keep_blank_values=True)
    if not pairs:
        return QueryState(mode="builder", groups=[], advanced_query="")

    known = set(known_fields) if known_fields is not None else DEFAULT_KNOWN_FIELDS
    clauses, has_unknown = _pairs_to_clauses(pairs, known)
    if has_unknown and strict:
        return QueryState(mode="advanced", groups=[], advanced_query=trimmed)

    return QueryState(mode="builder", groups=[Group(clauses=clauses)], advanced_query="")


def serialize_query_state(state: QueryState) -> str:
    if state.mode == "advanced":
        return (state.advanced_query or "").strip()

    pairs: list[tuple[str, str]] = []
    for group in state.groups:
        for clause in group.clauses:
            key = (clause.field or "").strip()
            values = clause.values if clause.values is not None else []
            for value in values:
                pairs.append((key, str(value).strip()))

    if not pairs:
        return ""
    return urlencode(pairs, doseq=True)


def query_state_from_dict(data: dict[str, Any] | None) -> QueryState:
    if not isinstance(data, dict):
        return QueryState()

    mode = data.get("mode", "builder")
    if mode not in ("builder", "advanced"):
        mode = "builder"

    advanced_query = data.get("advanced_query", data.get("advancedQuery", "")) or ""

    groups: list[Group] = []
    for group_data in data.get("groups", []) if isinstance(data.get("groups", []), list) else []:
        if not isinstance(group_data, dict):
            continue
        clauses: list[Clause] = []
        raw_clauses = group_data.get("clauses", [])
        if isinstance(raw_clauses, list):
            for clause_data in raw_clauses:
                if not isinstance(clause_data, dict):
                    continue
                field_name = str(clause_data.get("field", "") or "").strip()
                op_value = clause_data.get("op", "eq")
                op = op_value if op_value in _ALLOWED_OPS else "custom"
                values = clause_data.get("values", [])
                if values is None:
                    values_list: list[str] = []
                elif isinstance(values, list):
                    values_list = [str(value).strip() for value in values]
                else:
                    values_list = [str(values).strip()]
                clauses.append(Clause(field=field_name, op=op, values=values_list))
        groups.append(Group(clauses=clauses))

    return QueryState(mode=mode, groups=groups, advanced_query=str(advanced_query).strip())


def query_state_to_dict(state: QueryState) -> dict[str, Any]:
    return {
        "mode": state.mode,
        "groups": [
            {
                "clauses": [
                    {"field": clause.field, "op": clause.op, "values": list(clause.values)}
                    for clause in group.clauses
                ]
            }
            for group in state.groups
        ],
        "advanced_query": state.advanced_query,
    }


def _pairs_to_clauses(
    pairs: list[tuple[str, str]],
    known_fields: set[str],
) -> tuple[list[Clause], bool]:
    clauses: list[Clause] = []
    index: dict[tuple[str, str], Clause] = {}
    has_unknown = False
    for raw_key, raw_value in pairs:
        key = (raw_key or "").strip()
        value = (raw_value or "").strip()
        op: ClauseOp = "eq" if key in known_fields else "custom"
        if op == "custom":
            has_unknown = True
        clause_key = (key, op)
        clause = index.get(clause_key)
        if clause is None:
            clause = Clause(field=key, op=op, values=[])
            index[clause_key] = clause
            clauses.append(clause)
        clause.values.append(value)
    return clauses, has_unknown

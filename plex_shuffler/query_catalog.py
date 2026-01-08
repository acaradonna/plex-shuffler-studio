"""Curated query field catalog for the web query builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

InputKind = Literal["text", "number", "boolean", "multiselect", "custom"]
ValidationStatus = Literal["verified", "pending"]
QueryOp = Literal["eq", "contains", "gte", "lte", "exists", "custom"]


@dataclass(frozen=True)
class QueryField:
    key: str
    label: str
    input_kind: InputKind
    ops: tuple[QueryOp, ...]
    validation: ValidationStatus
    options_source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "input_kind": self.input_kind,
            "ops": list(self.ops),
            "validation": self.validation,
        }
        if self.options_source:
            payload["options_source"] = self.options_source
        return payload


QUERY_FIELD_CATALOG_V1: tuple[QueryField, ...] = (
    QueryField(
        key="genre",
        label="Genre",
        input_kind="multiselect",
        ops=("eq",),
        validation="verified",
        options_source="plex:genre",
    ),
    QueryField(
        key="unwatched",
        label="Unwatched only",
        input_kind="boolean",
        ops=("eq",),
        validation="verified",
    ),
    QueryField(
        key="year",
        label="Year",
        input_kind="number",
        ops=("eq", "gte", "lte"),
        validation="verified",
    ),
    QueryField(
        key="collection",
        label="Collection",
        input_kind="multiselect",
        ops=("eq",),
        validation="verified",
        options_source="plex:collection",
    ),
    QueryField(
        key="contentRating",
        label="Content rating",
        input_kind="multiselect",
        ops=("eq",),
        validation="verified",
        options_source="plex:contentRating",
    ),
    QueryField(
        key="studio",
        label="Studio",
        input_kind="multiselect",
        ops=("eq",),
        validation="verified",
        options_source="plex:studio",
    ),
    QueryField(
        key="title",
        label="Title contains",
        input_kind="text",
        ops=("contains",),
        validation="verified",
    ),
    QueryField(
        key="summary",
        label="Plot contains",
        input_kind="text",
        ops=("contains",),
        validation="pending",
    ),
    QueryField(
        key="actor",
        label="Actor",
        input_kind="multiselect",
        ops=("eq",),
        validation="verified",
        options_source="plex:actor",
    ),
    QueryField(
        key="director",
        label="Director",
        input_kind="multiselect",
        ops=("eq",),
        validation="verified",
        options_source="plex:director",
    ),
)


def catalog_for_api(*, include_unverified: bool = False) -> list[dict[str, Any]]:
    fields = []
    for field in QUERY_FIELD_CATALOG_V1:
        if field.validation != "verified" and not include_unverified:
            continue
        fields.append(field.to_dict())
    return fields


def known_field_keys() -> set[str]:
    return {field.key for field in QUERY_FIELD_CATALOG_V1 if field.validation == "verified"}


def plex_option_sources() -> set[str]:
    sources = set()
    for field in QUERY_FIELD_CATALOG_V1:
        if not field.options_source:
            continue
        if field.options_source.startswith("plex:"):
            sources.add(field.options_source.split(":", 1)[1])
    return sources


def default_op_for_field(key: str) -> str:
    for field in QUERY_FIELD_CATALOG_V1:
        if field.key == key:
            return field.ops[0]
    return "eq"

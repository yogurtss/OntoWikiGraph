from __future__ import annotations

from dataclasses import dataclass


ENTITY_TYPES = {
    "memory_product",
    "memory_family",
    "interface_standard",
    "component",
    "substructure",
    "timing_parameter",
    "performance_metric",
    "power_metric",
    "capacity_metric",
    "operating_condition",
    "process_technology",
    "material",
    "signal",
    "test_method",
    "failure_mode",
    "organization",
    "IMAGE",
    "TABLE",
    "FORMULA",
    "VIDEO",
}

RELATION_TYPES = {
    "related_to",
    "part_of",
    "contains",
    "connected_to",
    "interacts_with",
    "affects",
    "impacts",
    "depends_on",
    "causes",
    "enables",
    "measured_by",
    "has_timing",
    "has_bandwidth",
    "has_latency",
    "has_capacity",
    "consumes_power",
    "compatible_with",
    "uses_protocol",
    "specification_of",
    "tradeoff_with",
}

STRUCTURAL_RELATION_TYPES = {"parent_of", "next_sibling", "contains"}


@dataclass(frozen=True)
class Ontology:
    entity_types: frozenset[str]
    relation_types: frozenset[str]
    structural_relation_types: frozenset[str]


def default_ontology() -> Ontology:
    return Ontology(
        entity_types=frozenset(ENTITY_TYPES),
        relation_types=frozenset(RELATION_TYPES | STRUCTURAL_RELATION_TYPES),
        structural_relation_types=frozenset(STRUCTURAL_RELATION_TYPES),
    )


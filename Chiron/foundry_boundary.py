#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Neutral external-ontology boundary for Chiron records.

This module deliberately contains *no* network client, credential handling,
endpoint, SDK import, or vendor type.  It is a versioned contract that lets a
separately authorized integration translate Chiron records into an external
ontology without putting that vendor boundary inside the Chiron core.

The only adapters included here are intentionally non-delivering:

* ``UnconfiguredAdapter`` returns ``UNCONFIGURED``.
* ``DeterministicMockAdapter`` returns ``SIMULATED_NOT_DELIVERED`` and exposes
  the objects it *would* write for tests.

Neither status is a delivery acknowledgement.  A real transport belongs in a
separate, authorized deployment after its workspace, ontology, credentials,
permissions, audit policy, and live tests have been supplied.

Run ``python3 Chiron/foundry_boundary.py`` for a small offline self-test.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Dict, Iterable, Mapping, Optional, Protocol, Sequence, Tuple


CONTRACT_VERSION = "chiron.external-ontology/1"
CONFIG_VERSION = "chiron.external-integration-config/1"
MAPPING_VERSION = "chiron.external-ontology-mapping/1"


class ContractError(ValueError):
    """Raised when a record or mapping cannot honestly satisfy this contract."""


class RecordKind(str, Enum):
    """Canonical record kinds which can be represented outside Chiron."""

    SOURCE = "Source"
    ARTIFACT = "Artifact"
    CLAIM = "Claim"
    EVIDENCE = "Evidence"
    CONTRADICTION = "Contradiction"
    TRANSFORMATION = "Transformation"
    ENGINE_RUN = "EngineRun"
    MODEL_RUN = "ModelRun"
    CANDIDATE = "Candidate"
    CERTIFICATE = "Certificate"
    DISPOSITION = "Disposition"
    EXPERIMENT = "Experiment"
    USER_DECISION = "UserDecision"


class RelationKind(str, Enum):
    """Intentional, vendor-neutral edges between canonical records."""

    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONSUMES = "consumes"
    PRODUCES = "produces"
    CERTIFIES = "certifies"
    APPLIES_TO = "applies_to"
    PROPOSES = "proposes"
    RESOLVES = "resolves"
    DECIDES = "decides"


class ClaimVerdict(str, Enum):
    """The only Chiron claim-scale outcomes; these never imply probability."""

    VERIFIED = "VERIFIED"
    REFUTED = "REFUTED"
    REFUSED = "REFUSED"


class DispositionState(str, Enum):
    """Workflow state attached to a ``Disposition`` record.

    ``VERIFIED``, ``REFUTED``, and ``REFUSED`` retain their Chiron claim-scale
    meanings.  The remaining values describe process handling only; they must
    never upgrade a claim into a verification.
    """

    VERIFIED = "VERIFIED"
    REFUTED = "REFUTED"
    REFUSED = "REFUSED"
    PROVISIONAL = "PROVISIONAL"
    ESCALATED = "ESCALATED"
    UNSUPPORTED = "UNSUPPORTED"


class AdapterMode(str, Enum):
    """Modes deliberately available in this repository.

    There is no ``LIVE`` mode: this repository does not contain a live
    transport and must not pretend that a configuration is one.
    """

    UNCONFIGURED = "unconfigured"
    MOCK = "mock"


class IntegrationStatus(str, Enum):
    """Explicit outcomes of the included non-delivering adapters."""

    UNCONFIGURED = "UNCONFIGURED"
    SIMULATED_NOT_DELIVERED = "SIMULATED_NOT_DELIVERED"
    MISSING_LIVE_CONFIGURATION = "MISSING_LIVE_CONFIGURATION"
    LIVE_TRANSPORT_NOT_INCLUDED = "LIVE_TRANSPORT_NOT_INCLUDED"


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("%s must be a non-empty string" % name)


def _json_ready(value: Any) -> Any:
    """Return a strictly JSON-shaped, deterministic-friendly value.

    The integration boundary refuses opaque Python objects instead of quietly
    converting them with ``str()``.  Silent conversion would make an audit
    record look complete while losing the source representation.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError("record attribute keys must be strings")
            out[key] = _json_ready(item)
        return out
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    raise ContractError(
        "record values must be JSON-shaped; refusing %s" % type(value).__name__
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(_json_ready(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RecordLink:
    """A typed relationship from one canonical record to another."""

    relationship: RelationKind
    target_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.relationship, RelationKind):
            raise ContractError("relationship must be a RelationKind")
        _require_text(self.target_id, "target_id")

    def as_dict(self) -> Dict[str, str]:
        return {"relationship": self.relationship.value, "target_id": self.target_id}


@dataclass(frozen=True)
class CanonicalRecord:
    """One versioned Chiron-domain record, independent of any vendor SDK.

    ``attributes`` deliberately carries only JSON-shaped data.  Record kind,
    stable identifier, relationship edges, and any disposition remain typed so
    an external mapping can be checked before an integration writes anything.
    """

    record_type: RecordKind
    record_id: str
    attributes: Mapping[str, Any] = field(default_factory=dict)
    links: Tuple[RecordLink, ...] = ()
    disposition: Optional[DispositionState] = None

    def __post_init__(self) -> None:
        if not isinstance(self.record_type, RecordKind):
            raise ContractError("record_type must be a RecordKind")
        _require_text(self.record_id, "record_id")
        if not isinstance(self.attributes, Mapping):
            raise ContractError("attributes must be a mapping")
        _json_ready(self.attributes)
        if not isinstance(self.links, tuple) or not all(
                isinstance(link, RecordLink) for link in self.links):
            raise ContractError("links must be a tuple of RecordLink values")
        if self.record_type is RecordKind.DISPOSITION:
            if not isinstance(self.disposition, DispositionState):
                raise ContractError("a Disposition record needs a DispositionState")
        elif self.disposition is not None:
            raise ContractError(
                "only a Disposition record may carry disposition; link it to the "
                "claim, run, or certificate it records"
            )

    def as_dict(self) -> Dict[str, Any]:
        """Return the portable, versioned representation used for mapping."""
        return {
            "contract_version": CONTRACT_VERSION,
            "id": self.record_id,
            "kind": self.record_type.value,
            "attributes": _json_ready(self.attributes),
            "links": [link.as_dict() for link in self.links],
            "disposition": self.disposition.value if self.disposition else None,
        }


@dataclass(frozen=True)
class FieldBinding:
    """Map a canonical selector (``attributes.foo``) to an external field."""

    selector: str
    external_field: str

    def __post_init__(self) -> None:
        _require_text(self.selector, "selector")
        _require_text(self.external_field, "external_field")


@dataclass(frozen=True)
class ObjectTypeMapping:
    """A neutral mapping from one ``RecordKind`` to an external object type."""

    record_type: RecordKind
    external_object_type: str
    fields: Tuple[FieldBinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.record_type, RecordKind):
            raise ContractError("mapping record_type must be a RecordKind")
        _require_text(self.external_object_type, "external_object_type")
        if not self.fields or not all(isinstance(item, FieldBinding) for item in self.fields):
            raise ContractError("a mapping needs one or more FieldBinding values")
        names = [item.external_field for item in self.fields]
        if len(set(names)) != len(names):
            raise ContractError("external field names must be unique per object mapping")


def _standard_fields() -> Tuple[FieldBinding, ...]:
    return (
        FieldBinding("id", "chiron_id"),
        FieldBinding("kind", "chiron_kind"),
        FieldBinding("contract_version", "chiron_contract_version"),
        FieldBinding("attributes", "attributes"),
        FieldBinding("links", "links"),
        FieldBinding("disposition", "disposition"),
    )


def default_ontology_mapping() -> "OntologyMapping":
    """Return a complete neutral mapping that callers may rename explicitly.

    The external object-type strings are placeholders, not discovered ontology
    identifiers.  A live deployment must replace them with its authorized
    object types and fields before any separate transport is implemented.
    """
    return OntologyMapping(
        object_types=tuple(
            ObjectTypeMapping(
                record_type=record_type,
                external_object_type="chiron_" + record_type.value.lower(),
                fields=_standard_fields(),
            )
            for record_type in RecordKind
        )
    )


@dataclass(frozen=True)
class OntologyMapping:
    """A complete mapping for the versioned Chiron external-ontology contract."""

    contract_version: str = CONTRACT_VERSION
    mapping_version: str = MAPPING_VERSION
    object_types: Tuple[ObjectTypeMapping, ...] = ()

    def __post_init__(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise ContractError(
                "unsupported contract version %r (expected %s)" %
                (self.contract_version, CONTRACT_VERSION)
            )
        if self.mapping_version != MAPPING_VERSION:
            raise ContractError(
                "unsupported mapping version %r (expected %s)" %
                (self.mapping_version, MAPPING_VERSION)
            )
        if not isinstance(self.object_types, tuple) or not all(
                isinstance(item, ObjectTypeMapping) for item in self.object_types):
            raise ContractError("object_types must be a tuple of ObjectTypeMapping values")
        kinds = [item.record_type for item in self.object_types]
        if set(kinds) != set(RecordKind) or len(kinds) != len(set(kinds)):
            raise ContractError(
                "mapping must cover each canonical RecordKind exactly once"
            )

    def for_record_type(self, record_type: RecordKind) -> ObjectTypeMapping:
        for mapping in self.object_types:
            if mapping.record_type is record_type:
                return mapping
        raise ContractError("no mapping for record type %s" % record_type.value)


@dataclass(frozen=True)
class IntegrationConfig:
    """Configuration for the only modes shipped in this repository.

    A label is useful in test fixtures and audit traces, but it is not a
    workspace identifier, URL, secret, or delivery authorization.
    """

    schema_version: str = CONFIG_VERSION
    mode: AdapterMode = AdapterMode.UNCONFIGURED
    integration_label: str = "chiron-external-ontology"
    mapping: OntologyMapping = field(default_factory=default_ontology_mapping)

    def __post_init__(self) -> None:
        if self.schema_version != CONFIG_VERSION:
            raise ContractError(
                "unsupported config version %r (expected %s)" %
                (self.schema_version, CONFIG_VERSION)
            )
        if not isinstance(self.mode, AdapterMode):
            raise ContractError("mode must be an AdapterMode")
        _require_text(self.integration_label, "integration_label")
        if not isinstance(self.mapping, OntologyMapping):
            raise ContractError("mapping must be an OntologyMapping")


@dataclass(frozen=True)
class LiveIntegrationRequirements:
    """References a real deployment must provide; values are never secrets.

    This object only assesses readiness.  It deliberately cannot create a live
    client, read a credential, or make a request.  Secret material belongs in
    an authorized runtime's secret manager, referred to only by a non-secret
    name such as ``secret-manager:chiron-foundry-writer``.
    """

    workspace_reference: str = ""
    ontology_reference: str = ""
    credential_reference: str = ""
    authorization_reference: str = ""
    audit_log_reference: str = ""

    def missing(self) -> Tuple[str, ...]:
        values = (
            ("workspace_reference", self.workspace_reference),
            ("ontology_reference", self.ontology_reference),
            ("credential_reference", self.credential_reference),
            ("authorization_reference", self.authorization_reference),
            ("audit_log_reference", self.audit_log_reference),
        )
        return tuple(name for name, value in values if not isinstance(value, str) or not value.strip())


@dataclass(frozen=True)
class LiveReadiness:
    """An explicit non-success report for an absent live transport."""

    status: IntegrationStatus
    ready_to_deliver: bool
    missing: Tuple[str, ...]
    reason: str


def assess_live_readiness(requirements: LiveIntegrationRequirements) -> LiveReadiness:
    """Report what is missing without asserting a live connection exists."""
    if not isinstance(requirements, LiveIntegrationRequirements):
        raise ContractError("requirements must be a LiveIntegrationRequirements")
    missing = requirements.missing()
    if missing:
        return LiveReadiness(
            status=IntegrationStatus.MISSING_LIVE_CONFIGURATION,
            ready_to_deliver=False,
            missing=missing,
            reason="Live integration is not configured; no transport is present.",
        )
    return LiveReadiness(
        status=IntegrationStatus.LIVE_TRANSPORT_NOT_INCLUDED,
        ready_to_deliver=False,
        missing=(),
        reason=(
            "Configuration references are present, but this repository includes "
            "no authorized live transport, SDK client, or network delivery."
        ),
    )


@dataclass(frozen=True)
class ExternalObject:
    """A mapped object that a separately authorized transport could consume."""

    external_object_type: str
    external_id: str
    fields: Mapping[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "external_object_type": self.external_object_type,
            "external_id": self.external_id,
            "fields": _json_ready(self.fields),
        }


@dataclass(frozen=True)
class ExportPlan:
    """A deterministic, non-delivered batch produced from canonical records."""

    contract_version: str
    objects: Tuple[ExternalObject, ...]
    batch_digest: str


def _select(document: Mapping[str, Any], selector: str) -> Any:
    current: Any = document
    for part in selector.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise ContractError("selector %r does not exist in canonical record" % selector)
        current = current[part]
    return _json_ready(current)


def _external_id(record: CanonicalRecord) -> str:
    # Prefixing the canonical kind preserves uniqueness when different kinds
    # happen to share a human-readable ID.
    return "%s:%s" % (record.record_type.value, record.record_id)


def _map_record(record: CanonicalRecord, mapping: OntologyMapping) -> ExternalObject:
    object_mapping = mapping.for_record_type(record.record_type)
    source = record.as_dict()
    fields = {
        binding.external_field: _select(source, binding.selector)
        for binding in object_mapping.fields
    }
    return ExternalObject(
        external_object_type=object_mapping.external_object_type,
        external_id=_external_id(record),
        fields=fields,
    )


def plan_export(records: Iterable[CanonicalRecord], mapping: OntologyMapping) -> ExportPlan:
    """Map records deterministically, without attempting any delivery."""
    if not isinstance(mapping, OntologyMapping):
        raise ContractError("mapping must be an OntologyMapping")
    materialized = tuple(records)
    if not all(isinstance(record, CanonicalRecord) for record in materialized):
        raise ContractError("records must contain CanonicalRecord values")
    identities = [(record.record_type.value, record.record_id) for record in materialized]
    if len(identities) != len(set(identities)):
        raise ContractError("a batch cannot contain duplicate record type and id pairs")
    ordered = tuple(sorted(materialized, key=lambda record: (
        record.record_type.value, record.record_id
    )))
    objects = tuple(_map_record(record, mapping) for record in ordered)
    payload = {
        "contract_version": CONTRACT_VERSION,
        "mapping_version": mapping.mapping_version,
        "objects": [obj.as_dict() for obj in objects],
    }
    return ExportPlan(
        contract_version=CONTRACT_VERSION,
        objects=objects,
        batch_digest=_digest(payload),
    )


@dataclass(frozen=True)
class IntegrationReceipt:
    """An honest outcome from a boundary adapter.

    ``delivery_confirmed`` is false for every adapter in this repository.  The
    receipt intentionally has no field that could be mistaken for a remote
    acknowledgement.
    """

    contract_version: str
    status: IntegrationStatus
    delivery_confirmed: bool
    prepared_object_count: int
    batch_digest: str
    reason: str
    simulated_objects: Tuple[ExternalObject, ...] = ()


class IntegrationAdapter(Protocol):
    """Minimal seam for a separately authorized external adapter."""

    def export(self, records: Iterable[CanonicalRecord]) -> IntegrationReceipt:
        """Prepare a result.  Included adapters never deliver externally."""


class UnconfiguredAdapter:
    """Maps only enough to validate records, then explicitly does not deliver."""

    def __init__(self, config: IntegrationConfig):
        if config.mode is not AdapterMode.UNCONFIGURED:
            raise ContractError("UnconfiguredAdapter requires unconfigured mode")
        self._config = config

    def export(self, records: Iterable[CanonicalRecord]) -> IntegrationReceipt:
        plan = plan_export(records, self._config.mapping)
        return IntegrationReceipt(
            contract_version=CONTRACT_VERSION,
            status=IntegrationStatus.UNCONFIGURED,
            delivery_confirmed=False,
            prepared_object_count=len(plan.objects),
            batch_digest=plan.batch_digest,
            reason=(
                "No external integration is configured. Records were validated "
                "locally and were not delivered."
            ),
        )


class DeterministicMockAdapter:
    """Offline test adapter which reveals would-be objects but never sends them."""

    def __init__(self, config: IntegrationConfig):
        if config.mode is not AdapterMode.MOCK:
            raise ContractError("DeterministicMockAdapter requires mock mode")
        self._config = config

    def export(self, records: Iterable[CanonicalRecord]) -> IntegrationReceipt:
        plan = plan_export(records, self._config.mapping)
        return IntegrationReceipt(
            contract_version=CONTRACT_VERSION,
            status=IntegrationStatus.SIMULATED_NOT_DELIVERED,
            delivery_confirmed=False,
            prepared_object_count=len(plan.objects),
            batch_digest=plan.batch_digest,
            reason=(
                "Deterministic mock only: objects were simulated for inspection "
                "and were not delivered to an external system."
            ),
            simulated_objects=plan.objects,
        )


def adapter_for(config: IntegrationConfig) -> IntegrationAdapter:
    """Return one of the only safe adapters shipped in this repository."""
    if not isinstance(config, IntegrationConfig):
        raise ContractError("config must be an IntegrationConfig")
    if config.mode is AdapterMode.MOCK:
        return DeterministicMockAdapter(config)
    return UnconfiguredAdapter(config)


def _sample_records() -> Tuple[CanonicalRecord, ...]:
    """Small linked fixture shared by the self-test and documentation examples."""
    source = CanonicalRecord(
        record_type=RecordKind.SOURCE,
        record_id="source:demo",
        attributes={"content_sha256": "a" * 64, "label": "offline demonstration"},
    )
    claim = CanonicalRecord(
        record_type=RecordKind.CLAIM,
        record_id="claim:demo",
        attributes={"text": "2 + 2 = 4"},
        links=(RecordLink(RelationKind.DERIVED_FROM, source.record_id),),
    )
    evidence = CanonicalRecord(
        record_type=RecordKind.EVIDENCE,
        record_id="evidence:demo",
        attributes={"method": "exact arithmetic", "value": "4"},
        links=(RecordLink(RelationKind.SUPPORTS, claim.record_id),),
    )
    certificate = CanonicalRecord(
        record_type=RecordKind.CERTIFICATE,
        record_id="certificate:demo",
        attributes={"schema": "primus.certificate/2", "digest": "b" * 64},
        links=(
            RecordLink(RelationKind.CERTIFIES, claim.record_id),
            RecordLink(RelationKind.SUPPORTS, evidence.record_id),
        ),
    )
    disposition = CanonicalRecord(
        record_type=RecordKind.DISPOSITION,
        record_id="disposition:demo",
        attributes={"reason": "exact arithmetic matched"},
        links=(RecordLink(RelationKind.APPLIES_TO, claim.record_id),),
        disposition=DispositionState.VERIFIED,
    )
    return source, claim, evidence, certificate, disposition


def selftest() -> int:
    """Offline proof that mapping is deterministic and never claims delivery."""
    records = _sample_records()
    mapping = default_ontology_mapping()
    first = plan_export(records, mapping)
    second = plan_export(tuple(reversed(records)), mapping)
    assert first.batch_digest == second.batch_digest
    assert len(first.objects) == len(records)
    assert {obj.external_object_type for obj in first.objects} >= {
        "chiron_source", "chiron_claim", "chiron_evidence",
        "chiron_certificate", "chiron_disposition",
    }
    unconfigured = adapter_for(IntegrationConfig()).export(records)
    assert unconfigured.status is IntegrationStatus.UNCONFIGURED
    assert not unconfigured.delivery_confirmed
    mock_config = IntegrationConfig(mode=AdapterMode.MOCK)
    mock = adapter_for(mock_config).export(records)
    assert mock.status is IntegrationStatus.SIMULATED_NOT_DELIVERED
    assert not mock.delivery_confirmed
    assert mock.batch_digest == first.batch_digest
    assert len(mock.simulated_objects) == len(records)
    incomplete = assess_live_readiness(LiveIntegrationRequirements())
    assert incomplete.status is IntegrationStatus.MISSING_LIVE_CONFIGURATION
    complete_references = LiveIntegrationRequirements(
        workspace_reference="workspace:authorized-name",
        ontology_reference="ontology:approved-mapping",
        credential_reference="secret-manager:writer-reference",
        authorization_reference="approval:change-ticket",
        audit_log_reference="audit:external-writes",
    )
    no_transport = assess_live_readiness(complete_references)
    assert no_transport.status is IntegrationStatus.LIVE_TRANSPORT_NOT_INCLUDED
    assert not no_transport.ready_to_deliver
    print("[PASS] deterministic map is order-independent (%d objects)" % len(first.objects))
    print("[PASS] unconfigured and mock adapters do not claim delivery")
    print("[PASS] live references still refuse without a transport")
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest())

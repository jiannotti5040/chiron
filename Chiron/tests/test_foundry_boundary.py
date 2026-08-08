#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Offline regression gates for the external-ontology / Foundry boundary.

Run: python3 Chiron/tests/test_foundry_boundary.py
"""
import os
import sys


CHIRON = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, CHIRON)

import foundry_boundary as boundary


def records():
    return boundary._sample_records()


def test_default_mapping_covers_every_canonical_record_kind_once():
    mapping = boundary.default_ontology_mapping()
    mapped_kinds = [item.record_type for item in mapping.object_types]
    assert set(mapped_kinds) == set(boundary.RecordKind)
    assert len(mapped_kinds) == len(set(mapped_kinds))


def test_mapping_is_deterministic_and_preserves_typed_relationships():
    fixture = records()
    first = boundary.plan_export(fixture, boundary.default_ontology_mapping())
    second = boundary.plan_export(tuple(reversed(fixture)), boundary.default_ontology_mapping())
    assert first.batch_digest == second.batch_digest
    claim = next(obj for obj in first.objects if obj.external_id == "Claim:claim:demo")
    assert claim.fields["links"] == [{
        "relationship": "derived_from", "target_id": "source:demo"
    }]


def test_unconfigured_adapter_refuses_to_claim_delivery():
    receipt = boundary.adapter_for(boundary.IntegrationConfig()).export(records())
    assert receipt.status is boundary.IntegrationStatus.UNCONFIGURED
    assert receipt.delivery_confirmed is False
    assert receipt.simulated_objects == ()
    assert receipt.prepared_object_count == len(records())


def test_mock_adapter_is_explicitly_simulated_not_delivered():
    config = boundary.IntegrationConfig(mode=boundary.AdapterMode.MOCK)
    receipt = boundary.adapter_for(config).export(records())
    assert receipt.status is boundary.IntegrationStatus.SIMULATED_NOT_DELIVERED
    assert receipt.delivery_confirmed is False
    assert len(receipt.simulated_objects) == len(records())
    assert "not delivered" in receipt.reason.lower()


def test_live_references_are_not_mistaken_for_a_live_connection():
    incomplete = boundary.assess_live_readiness(boundary.LiveIntegrationRequirements())
    assert incomplete.status is boundary.IntegrationStatus.MISSING_LIVE_CONFIGURATION
    assert incomplete.ready_to_deliver is False
    complete = boundary.LiveIntegrationRequirements(
        workspace_reference="workspace:approved",
        ontology_reference="ontology:approved",
        credential_reference="secret-manager:approved",
        authorization_reference="approval:approved",
        audit_log_reference="audit:approved",
    )
    no_transport = boundary.assess_live_readiness(complete)
    assert no_transport.status is boundary.IntegrationStatus.LIVE_TRANSPORT_NOT_INCLUDED
    assert no_transport.ready_to_deliver is False


def test_contract_rejects_opaque_data_and_ambiguous_disposition_placement():
    try:
        boundary.CanonicalRecord(
            record_type=boundary.RecordKind.SOURCE,
            record_id="source:opaque",
            attributes={"opaque": object()},
        )
    except boundary.ContractError:
        pass
    else:
        raise AssertionError("opaque object should be refused")

    try:
        boundary.CanonicalRecord(
            record_type=boundary.RecordKind.CLAIM,
            record_id="claim:bad-disposition",
            disposition=boundary.DispositionState.VERIFIED,
        )
    except boundary.ContractError:
        pass
    else:
        raise AssertionError("only Disposition records may carry disposition")


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok -", test.__name__)
    print("ALL PASSED (%d)" % len(tests))

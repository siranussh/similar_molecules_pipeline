import sys
import os
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fingerprints import compute_morgan_fingerprint  # noqa: E402


def test_valid_smiles_returns_fingerprint():
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"

    fingerprint = compute_morgan_fingerprint(aspirin_smiles)

    assert fingerprint is not None


def test_fingerprint_has_requested_length():
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"

    fingerprint = compute_morgan_fingerprint(aspirin_smiles, n_bits=2048)

    assert len(fingerprint) == 2048


def test_fingerprint_length_respects_custom_n_bits():
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"

    fingerprint = compute_morgan_fingerprint(aspirin_smiles, n_bits=1024)

    assert len(fingerprint) == 1024


def test_invalid_smiles_returns_none():
    invalid_smiles = "this is not a valid smiles string"

    fingerprint = compute_morgan_fingerprint(invalid_smiles)

    assert fingerprint is None


def test_empty_smiles_returns_none():
    fingerprint = compute_morgan_fingerprint("")

    assert fingerprint is None


def test_same_molecule_produces_identical_fingerprints():
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"

    fingerprint_a = compute_morgan_fingerprint(aspirin_smiles)
    fingerprint_b = compute_morgan_fingerprint(aspirin_smiles)

    assert fingerprint_a.ToBitString() == fingerprint_b.ToBitString()


def test_real_chembl_sample_fingerprints_successfully():
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "chembl_sample.csv"
    )

    with open(sample_path, newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)[:50]

    assert len(rows) == 50

    failed_ids = []

    for row in rows:
        fingerprint = compute_morgan_fingerprint(row["canonical_smiles"])

        if fingerprint is None:
            failed_ids.append(row["chembl_id"])

    assert failed_ids == []

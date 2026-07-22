import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fingerprints import compute_morgan_fingerprint  # noqa: E402
from similarity import compute_tanimoto_similarity  # noqa: E402


def test_identical_molecules_have_similarity_of_one():
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"

    fingerprint = compute_morgan_fingerprint(aspirin_smiles)
    similarity = compute_tanimoto_similarity(fingerprint, fingerprint)

    assert similarity == 1.0


def test_structurally_related_molecules_score_high():
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    salicylic_acid_smiles = "OC(=O)C1=CC=CC=C1O"

    aspirin_fp = compute_morgan_fingerprint(aspirin_smiles)
    salicylic_acid_fp = compute_morgan_fingerprint(salicylic_acid_smiles)

    similarity = compute_tanimoto_similarity(aspirin_fp, salicylic_acid_fp)

    assert similarity > 0.4


def test_structurally_unrelated_molecules_score_low():
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    caffeine_smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"

    aspirin_fp = compute_morgan_fingerprint(aspirin_smiles)
    caffeine_fp = compute_morgan_fingerprint(caffeine_smiles)

    similarity = compute_tanimoto_similarity(aspirin_fp, caffeine_fp)

    assert similarity < 0.15


def test_related_pair_scores_higher_than_unrelated_pair():
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    salicylic_acid_smiles = "OC(=O)C1=CC=CC=C1O"
    caffeine_smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"

    aspirin_fp = compute_morgan_fingerprint(aspirin_smiles)
    salicylic_acid_fp = compute_morgan_fingerprint(salicylic_acid_smiles)
    caffeine_fp = compute_morgan_fingerprint(caffeine_smiles)

    related_similarity = compute_tanimoto_similarity(
        aspirin_fp, salicylic_acid_fp
    )
    unrelated_similarity = compute_tanimoto_similarity(
        aspirin_fp, caffeine_fp
    )

    assert related_similarity > unrelated_similarity


def test_similarity_is_symmetric():
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    caffeine_smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"

    aspirin_fp = compute_morgan_fingerprint(aspirin_smiles)
    caffeine_fp = compute_morgan_fingerprint(caffeine_smiles)

    similarity_a_to_b = compute_tanimoto_similarity(aspirin_fp, caffeine_fp)
    similarity_b_to_a = compute_tanimoto_similarity(caffeine_fp, aspirin_fp)

    assert similarity_a_to_b == similarity_b_to_a

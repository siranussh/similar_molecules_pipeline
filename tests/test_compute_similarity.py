import os
import sys
from unittest.mock import MagicMock, patch

from rdkit import DataStructs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fingerprints import compute_morgan_fingerprint  # noqa: E402
import compute_similarity  # noqa: E402


def test_fetch_structures_query_without_limit():
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchall.return_value = []

    compute_similarity.fetch_structures(connection, limit=None)

    called_query = cursor.execute.call_args[0][0]
    assert "LIMIT" not in called_query


def test_fetch_structures_query_with_limit():
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchall.return_value = []

    compute_similarity.fetch_structures(connection, limit=50)

    called_query = cursor.execute.call_args[0][0]
    assert "LIMIT 50" in called_query


def test_fingerprint_structures_skips_invalid_smiles():
    structures = [
        ("CHEMBL1", "CC(=O)OC1=CC=CC=C1C(=O)O"),
        ("CHEMBL2", "not a valid smiles"),
    ]

    fingerprinted, failed_count = compute_similarity.fingerprint_structures(
        structures
    )

    assert failed_count == 1
    assert len(fingerprinted) == 1
    assert fingerprinted[0][0] == "CHEMBL1"


def test_select_source_molecules_respects_count():
    fingerprinted = [(f"CHEMBL{i}", None) for i in range(200)]

    sources = compute_similarity.select_source_molecules(
        fingerprinted, count=100
    )

    assert len(sources) == 100
    assert sources[0][0] == "CHEMBL0"
    assert sources[-1][0] == "CHEMBL99"


def test_compute_top10_excludes_self():
    aspirin = compute_morgan_fingerprint("CC(=O)OC1=CC=CC=C1C(=O)O")
    fingerprinted = [("CHEMBL_SOURCE", aspirin), ("CHEMBL_SOURCE", aspirin)]

    top10 = compute_similarity.compute_top10_for_source(
        "CHEMBL_SOURCE", aspirin, fingerprinted
    )

    target_ids = [target_id for target_id, score, flag in top10]
    assert "CHEMBL_SOURCE" not in target_ids


def test_compute_top10_returns_highest_scores_first():
    aspirin = compute_morgan_fingerprint("CC(=O)OC1=CC=CC=C1C(=O)O")
    salicylic_acid = compute_morgan_fingerprint("OC(=O)C1=CC=CC=C1O")
    caffeine = compute_morgan_fingerprint("CN1C=NC2=C1C(=O)N(C(=O)N2C)C")

    fingerprinted = [
        ("SOURCE", aspirin),
        ("SALICYLIC", salicylic_acid),
        ("CAFFEINE", caffeine),
    ]

    top10 = compute_similarity.compute_top10_for_source(
        "SOURCE", aspirin, fingerprinted
    )

    assert top10[0][0] == "SALICYLIC"
    assert top10[0][1] > top10[1][1]


def test_compute_top10_flags_only_boundary_ties():
    fingerprinted = [("SRC", "src_fp")]
    for i in range(15):
        fingerprinted.append((f"T{i}", f"fp{i}"))

    fake_scores = {
        "fp0": 0.9, "fp1": 0.8, "fp2": 0.7, "fp3": 0.6,
        "fp4": 0.5, "fp5": 0.4, "fp6": 0.3, "fp7": 0.2,
        "fp8": 0.1, "fp9": 0.1, "fp10": 0.1, "fp11": 0.1,
        "fp12": 0.05, "fp13": 0.01, "fp14": 0.001,
    }

    def fake_tanimoto(fp_a, fp_b):
        return fake_scores[fp_b]

    with patch.object(
        DataStructs, "TanimotoSimilarity", side_effect=fake_tanimoto
    ):
        result = compute_similarity.compute_top10_for_source(
            "SRC", "src_fp", fingerprinted
        )

    flags = {target_id: flag for target_id, score, flag in result}
    assert flags["T8"] is True
    assert flags["T9"] is True
    assert flags["T0"] is False


def test_compute_top10_no_flag_when_boundary_score_is_unique():
    fingerprinted = [("SRC", "src_fp")]
    for i in range(12):
        fingerprinted.append((f"T{i}", f"fp{i}"))

    fake_scores = {
        f"fp{i}": round(0.9 - i * 0.08, 2) for i in range(12)
    }

    def fake_tanimoto(fp_a, fp_b):
        return fake_scores[fp_b]

    with patch.object(
        DataStructs, "TanimotoSimilarity", side_effect=fake_tanimoto
    ):
        result = compute_similarity.compute_top10_for_source(
            "SRC", "src_fp", fingerprinted
        )

    flags = [flag for target_id, score, flag in result]
    assert all(flag is False for flag in flags)


def test_compute_all_similarities_produces_expected_row_count():
    aspirin = compute_morgan_fingerprint("CC(=O)OC1=CC=CC=C1C(=O)O")
    fingerprinted = [(f"CHEMBL{i}", aspirin) for i in range(15)]
    sources = fingerprinted[:2]

    results = compute_similarity.compute_all_similarities(
        sources, fingerprinted
    )

    assert len(results) == 20
    source_ids = {row[0] for row in results}
    assert source_ids == {"CHEMBL0", "CHEMBL1"}


def test_write_to_fact_similarity_truncates_and_inserts():
    connection = MagicMock()
    cursor = connection.cursor.return_value

    results = [
        ("SRC1", "TGT1", 0.9, False),
        ("SRC1", "TGT2", 0.8, True),
    ]

    row_count = compute_similarity.write_to_fact_similarity(
        connection, results
    )

    cursor.execute.assert_called_once_with(
        "TRUNCATE TABLE gold.fact_similarity"
    )
    cursor.executemany.assert_called_once()
    connection.commit.assert_called_once()
    assert row_count == 2

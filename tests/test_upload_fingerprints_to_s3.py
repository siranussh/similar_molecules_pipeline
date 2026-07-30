import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import upload_fingerprints_to_s3  # noqa: E402


def test_fingerprint_batch_skips_invalid_smiles():
    structures = [
        ("CHEMBL1", "CC(=O)OC1=CC=CC=C1C(=O)O"),
        ("CHEMBL2", "not a valid smiles"),
    ]

    dataframe, failed_count = upload_fingerprints_to_s3.fingerprint_batch(
        structures
    )

    assert failed_count == 1
    assert len(dataframe) == 1
    assert dataframe.iloc[0]["chembl_id"] == "CHEMBL1"


def test_fingerprint_batch_empty_input_returns_empty_dataframe():
    dataframe, failed_count = upload_fingerprints_to_s3.fingerprint_batch([])

    assert len(dataframe) == 0
    assert failed_count == 0


def test_run_fingerprint_and_save_processes_multiple_batches(tmp_path):
    all_structures = [
        (f"CHEMBL{i}", "CC(=O)OC1=CC=CC=C1C(=O)O") for i in range(5)
    ]

    def fake_fetch(connection, offset, batch_size):
        return all_structures[offset:offset + batch_size]

    output_path = os.path.join(tmp_path, "test.parquet")

    with patch.object(
        upload_fingerprints_to_s3, "fetch_structures_batch",
        side_effect=fake_fetch,
    ):
        total_written, total_failed = (
            upload_fingerprints_to_s3.run_fingerprint_and_save(
                MagicMock(), output_path, batch_size=2
            )
        )

    assert total_written == 5
    assert total_failed == 0
    assert os.path.exists(output_path)


def test_run_fingerprint_and_save_stops_on_empty_batch(tmp_path):
    output_path = os.path.join(tmp_path, "empty.parquet")

    with patch.object(
        upload_fingerprints_to_s3, "fetch_structures_batch",
        return_value=[],
    ):
        total_written, total_failed = (
            upload_fingerprints_to_s3.run_fingerprint_and_save(
                MagicMock(), output_path, batch_size=100
            )
        )

    assert total_written == 0
    assert total_failed == 0
    assert not os.path.exists(output_path)


def test_run_fingerprint_and_save_result_is_readable(tmp_path):
    import pandas as pd

    all_structures = [
        ("CHEMBL1", "CC(=O)OC1=CC=CC=C1C(=O)O"),
        ("CHEMBL2", "OC(=O)C1=CC=CC=C1O"),
    ]

    def fake_fetch(connection, offset, batch_size):
        return all_structures[offset:offset + batch_size]

    output_path = os.path.join(tmp_path, "readable.parquet")

    with patch.object(
        upload_fingerprints_to_s3, "fetch_structures_batch",
        side_effect=fake_fetch,
    ):
        upload_fingerprints_to_s3.run_fingerprint_and_save(
            MagicMock(), output_path, batch_size=1
        )

    reloaded = pd.read_parquet(output_path)
    assert list(reloaded["chembl_id"]) == ["CHEMBL1", "CHEMBL2"]

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fingerprints import compute_morgan_fingerprint  # noqa: E402
import compute_full_similarity_to_s3  # noqa: E402
from compute_full_similarity_to_s3 import (  # noqa: E402
    compute_full_similarity_for_source,
)


def test_compute_full_similarity_excludes_self():
    aspirin = compute_morgan_fingerprint("CC(=O)OC1=CC=CC=C1C(=O)O")
    fingerprinted = [
        ("SOURCE", aspirin),
        ("OTHER", aspirin),
    ]

    dataframe = compute_full_similarity_for_source(
        "SOURCE", aspirin, fingerprinted
    )

    assert "SOURCE" not in list(dataframe["target_chembl_id"])
    assert len(dataframe) == 1


def test_compute_full_similarity_includes_every_other_molecule():
    aspirin = compute_morgan_fingerprint("CC(=O)OC1=CC=CC=C1C(=O)O")
    fingerprinted = [(f"CHEMBL{i}", aspirin) for i in range(50)]

    dataframe = compute_full_similarity_for_source(
        "CHEMBL0", aspirin, fingerprinted
    )

    assert len(dataframe) == 49


def test_compute_full_similarity_scores_are_not_top10_limited():
    aspirin = compute_morgan_fingerprint("CC(=O)OC1=CC=CC=C1C(=O)O")
    fingerprinted = [(f"CHEMBL{i}", aspirin) for i in range(25)]

    dataframe = compute_full_similarity_for_source(
        "CHEMBL0", aspirin, fingerprinted
    )

    assert len(dataframe) == 24
    assert list(dataframe.columns) == [
        "target_chembl_id", "similarity_score"
    ]


def test_save_and_upload_source_table_creates_and_removes_local_file(
    tmp_path,
):
    import pandas as pd

    dataframe = pd.DataFrame({
        "target_chembl_id": ["CHEMBL1"],
        "similarity_score": [0.5],
    })
    local_dir = os.path.join(tmp_path, "full_similarity")

    with patch.object(
        compute_full_similarity_to_s3, "upload_file",
        return_value="s3://bucket/key.parquet",
    ) as mock_upload:
        uri = compute_full_similarity_to_s3.save_and_upload_source_table(
            dataframe, "CHEMBL_SOURCE", "bucket", "subfolder",
            local_dir=local_dir,
        )

    assert uri == "s3://bucket/key.parquet"
    mock_upload.assert_called_once()
    saved_local_path = mock_upload.call_args[0][0]
    assert not os.path.exists(saved_local_path)


def test_save_and_upload_source_table_uses_correct_s3_key():
    import pandas as pd

    dataframe = pd.DataFrame({
        "target_chembl_id": ["CHEMBL1"],
        "similarity_score": [0.5],
    })

    with patch.object(
        compute_full_similarity_to_s3, "upload_file",
        return_value="s3://bucket/key.parquet",
    ) as mock_upload:
        compute_full_similarity_to_s3.save_and_upload_source_table(
            dataframe, "CHEMBL42", "my-bucket", "siranush_hakobyan",
            local_dir="full_similarity",
        )

    called_s3_key = mock_upload.call_args[0][2]
    assert called_s3_key == (
        "siranush_hakobyan/full_similarity/CHEMBL42.parquet"
    )

import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import ingestion  # noqa: E402


def test_ingest_chembl_id_lookup_query_without_limit():
    with patch.object(ingestion.chembl_downloader, "query") as mock_query:
        mock_query.return_value = pd.DataFrame()
        ingestion.ingest_chembl_id_lookup(limit=None)

    called_query = mock_query.call_args[0][0]
    assert "FROM chembl_id_lookup" in called_query
    assert "LIMIT" not in called_query


def test_ingest_chembl_id_lookup_query_with_limit():
    with patch.object(ingestion.chembl_downloader, "query") as mock_query:
        mock_query.return_value = pd.DataFrame()
        ingestion.ingest_chembl_id_lookup(limit=100)

    called_query = mock_query.call_args[0][0]
    assert "LIMIT 100" in called_query


def test_ingest_compound_structures_filters_null_smiles():
    with patch.object(ingestion.chembl_downloader, "query") as mock_query:
        mock_query.return_value = pd.DataFrame()
        ingestion.ingest_compound_structures(limit=None)

    called_query = mock_query.call_args[0][0]
    assert "canonical_smiles IS NOT NULL" in called_query


def test_save_to_parquet_creates_output_dir(tmp_path):
    output_dir = os.path.join(tmp_path, "new_dir")
    dataframe = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

    output_path = ingestion.save_to_parquet(
        dataframe, output_dir, "test.parquet"
    )

    assert os.path.exists(output_dir)
    assert os.path.exists(output_path)


def test_save_to_parquet_roundtrip(tmp_path):
    dataframe = pd.DataFrame({"chembl_id": ["CHEMBL1", "CHEMBL2"]})

    output_path = ingestion.save_to_parquet(
        dataframe, str(tmp_path), "test.parquet"
    )
    reloaded = pd.read_parquet(output_path)

    assert list(reloaded["chembl_id"]) == ["CHEMBL1", "CHEMBL2"]


def test_run_ingestion_returns_correct_row_counts(tmp_path):
    fake_id_lookup = pd.DataFrame({"chembl_id": ["A", "B"]})
    fake_molecule_dict = pd.DataFrame({"chembl_id": ["A"]})
    fake_properties = pd.DataFrame({"molregno": [1, 2, 3]})
    fake_structures = pd.DataFrame({"molregno": [1]})

    with patch.object(
        ingestion, "ingest_chembl_id_lookup", return_value=fake_id_lookup
    ), patch.object(
        ingestion, "ingest_molecule_dictionary",
        return_value=fake_molecule_dict
    ), patch.object(
        ingestion, "ingest_compound_properties",
        return_value=fake_properties
    ), patch.object(
        ingestion, "ingest_compound_structures",
        return_value=fake_structures
    ):
        results = ingestion.run_ingestion(output_dir=str(tmp_path))

    assert results["chembl_id_lookup.parquet"][1] == 2
    assert results["molecule_dictionary.parquet"][1] == 1
    assert results["compound_properties.parquet"][1] == 3
    assert results["compound_structures.parquet"][1] == 1

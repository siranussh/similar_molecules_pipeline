import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import load_to_bronze  # noqa: E402


def make_mock_connection():
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


def test_load_parquet_to_table_truncates_and_copies(tmp_path):
    connection, cursor = make_mock_connection()
    dataframe = pd.DataFrame({
        "chembl_id": ["CHEMBL1", "CHEMBL2"],
        "status": ["ACTIVE", "ACTIVE"],
    })
    parquet_path = os.path.join(tmp_path, "test.parquet")
    dataframe.to_parquet(parquet_path, index=False)

    row_count = load_to_bronze.load_parquet_to_table(
        connection, parquet_path, "bronze", "chembl_id_lookup",
        ["chembl_id", "status"],
    )

    cursor.execute.assert_called_once_with(
        "TRUNCATE TABLE bronze.chembl_id_lookup"
    )
    assert cursor.copy_expert.called
    assert connection.commit.call_count == 2
    assert row_count == 2


def test_load_parquet_to_table_casts_int_columns_with_nulls(tmp_path):
    connection, cursor = make_mock_connection()
    dataframe = pd.DataFrame({
        "molregno": [1, 2, 3],
        "heavy_atoms": [24.0, None, 30.0],
    })
    parquet_path = os.path.join(tmp_path, "test.parquet")
    dataframe.to_parquet(parquet_path, index=False)

    captured = []
    cursor.copy_expert.side_effect = (
        lambda sql, buf: captured.append(buf.getvalue())
    )

    load_to_bronze.load_parquet_to_table(
        connection, parquet_path, "bronze", "compound_properties",
        ["molregno", "heavy_atoms"], int_columns=["heavy_atoms"],
    )

    csv_content = "".join(captured)
    assert "24.0" not in csv_content
    assert "24" in csv_content


def test_load_parquet_to_table_processes_multiple_batches(tmp_path):
    connection, cursor = make_mock_connection()
    dataframe = pd.DataFrame({
        "molregno": list(range(10)),
        "chembl_id": [f"CHEMBL{i}" for i in range(10)],
    })
    parquet_path = os.path.join(tmp_path, "test.parquet")
    dataframe.to_parquet(parquet_path, index=False)

    row_count = load_to_bronze.load_parquet_to_table(
        connection, parquet_path, "bronze", "molecule_dictionary",
        ["molregno", "chembl_id"], batch_size=3,
    )

    assert row_count == 10
    assert cursor.copy_expert.call_count == 4


def test_load_parquet_to_table_retries_on_operational_error(tmp_path):
    connection, cursor = make_mock_connection()
    dataframe = pd.DataFrame({
        "chembl_id": ["CHEMBL1", "CHEMBL2"],
        "status": ["ACTIVE", "ACTIVE"],
    })
    parquet_path = os.path.join(tmp_path, "test.parquet")
    dataframe.to_parquet(parquet_path, index=False)

    cursor.copy_expert.side_effect = [
        psycopg2.OperationalError("connection already closed"),
        None,
    ]

    with patch.object(load_to_bronze.time, "sleep"):
        row_count = load_to_bronze.load_parquet_to_table(
            connection, parquet_path, "bronze", "chembl_id_lookup",
            ["chembl_id", "status"],
        )

    assert row_count == 2
    assert cursor.copy_expert.call_count == 2
    assert connection.rollback.call_count == 1


def test_load_parquet_to_table_raises_after_max_retries(tmp_path):
    connection, cursor = make_mock_connection()
    dataframe = pd.DataFrame({
        "chembl_id": ["CHEMBL1", "CHEMBL2"],
        "status": ["ACTIVE", "ACTIVE"],
    })
    parquet_path = os.path.join(tmp_path, "test.parquet")
    dataframe.to_parquet(parquet_path, index=False)

    cursor.copy_expert.side_effect = psycopg2.OperationalError(
        "connection already closed"
    )

    with patch.object(load_to_bronze.time, "sleep"):
        try:
            load_to_bronze.load_parquet_to_table(
                connection, parquet_path, "bronze", "chembl_id_lookup",
                ["chembl_id", "status"], max_retries=3,
            )
            assert False, "expected OperationalError to be raised"
        except psycopg2.OperationalError:
            pass

    assert cursor.copy_expert.call_count == 3
    assert connection.rollback.call_count == 3


def test_get_connection_passes_keepalive_and_timeout_options():
    env = {
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "5433",
        "DB_NAME": "shakobyan_db",
        "DB_USER": "shakobyan",
        "DB_PASSWORD": "secret",
    }

    with patch.dict(os.environ, env), patch.object(
        load_to_bronze.psycopg2, "connect"
    ) as mock_connect:
        load_to_bronze.get_connection()

    _, kwargs = mock_connect.call_args
    assert kwargs["connect_timeout"] == 10
    assert kwargs["keepalives"] == 1
    assert kwargs["keepalives_idle"] == 30
    assert kwargs["keepalives_interval"] == 10
    assert kwargs["keepalives_count"] == 3
    assert kwargs["options"] == "-c statement_timeout=120000"


def test_load_chembl_id_lookup_calls_shared_loader_correctly(tmp_path):
    connection, _ = make_mock_connection()

    with patch.object(
        load_to_bronze, "load_parquet_to_table", return_value=1
    ) as mock_load:
        result = load_to_bronze.load_chembl_id_lookup(
            connection, str(tmp_path)
        )

    assert result == 1
    called_args = mock_load.call_args[0]
    assert called_args[2] == "bronze"
    assert called_args[3] == "chembl_id_lookup"


def test_run_load_calls_all_four_loaders_and_closes_connection():
    connection, _ = make_mock_connection()

    with patch.object(
        load_to_bronze, "get_connection", return_value=connection
    ), patch.object(
        load_to_bronze, "load_chembl_id_lookup", return_value=100
    ), patch.object(
        load_to_bronze, "load_molecule_dictionary", return_value=200
    ), patch.object(
        load_to_bronze, "load_compound_properties", return_value=300
    ), patch.object(
        load_to_bronze, "load_compound_structures", return_value=400
    ):
        results = load_to_bronze.run_load(input_dir="fake_dir")

    assert results == {
        "chembl_id_lookup": 100,
        "molecule_dictionary": 200,
        "compound_properties": 300,
        "compound_structures": 400,
    }
    connection.close.assert_called_once()

import io
import os

import psycopg2
import pyarrow.parquet as pq
from dotenv import load_dotenv

load_dotenv()

DEFAULT_INPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "ingested_data"
)


def get_connection():
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    database = os.environ["DB_NAME"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]

    return psycopg2.connect(
        host=host, port=port, dbname=database, user=user, password=password
    )


def load_parquet_to_table(
    connection, parquet_path, schema, table, columns,
    int_columns=None, batch_size=1000000,
):
    cursor = connection.cursor()
    cursor.execute(f"TRUNCATE TABLE {schema}.{table}")

    column_list = ", ".join(columns)
    copy_sql = (
        f"COPY {schema}.{table} ({column_list}) "
        f"FROM STDIN WITH (FORMAT csv, NULL '')"
    )

    parquet_file = pq.ParquetFile(parquet_path)
    total_rows = 0

    for batch in parquet_file.iter_batches(
        batch_size=batch_size, columns=columns
    ):
        dataframe = batch.to_pandas()

        if int_columns is not None:
            for column in int_columns:
                dataframe[column] = dataframe[column].astype("Int64")

        buffer = io.StringIO()
        dataframe.to_csv(buffer, index=False, header=False)
        buffer.seek(0)

        cursor.copy_expert(copy_sql, buffer)
        total_rows += len(dataframe)

    connection.commit()
    cursor.close()

    return total_rows


def load_chembl_id_lookup(connection, input_dir):
    parquet_path = os.path.join(input_dir, "chembl_id_lookup.parquet")
    columns = ["chembl_id", "entity_type", "entity_id", "status"]
    return load_parquet_to_table(
        connection,
        parquet_path,
        "bronze",
        "chembl_id_lookup",
        columns,
        int_columns=["entity_id"],
    )


def load_molecule_dictionary(connection, input_dir):
    parquet_path = os.path.join(input_dir, "molecule_dictionary.parquet")
    columns = [
        "molregno",
        "chembl_id",
        "pref_name",
        "molecule_type",
        "max_phase",
        "therapeutic_flag",
        "withdrawn_flag",
    ]
    return load_parquet_to_table(
        connection,
        parquet_path,
        "bronze",
        "molecule_dictionary",
        columns,
        int_columns=["therapeutic_flag", "withdrawn_flag"],
    )


def load_compound_properties(connection, input_dir):
    parquet_path = os.path.join(input_dir, "compound_properties.parquet")
    columns = [
        "molregno",
        "mw_freebase",
        "full_mwt",
        "alogp",
        "hba",
        "hbd",
        "psa",
        "aromatic_rings",
        "heavy_atoms",
        "qed_weighted",
    ]
    return load_parquet_to_table(
        connection,
        parquet_path,
        "bronze",
        "compound_properties",
        columns,
        int_columns=["hba", "hbd", "aromatic_rings", "heavy_atoms"],
    )


def load_compound_structures(connection, input_dir):
    parquet_path = os.path.join(input_dir, "compound_structures.parquet")
    columns = [
        "molregno",
        "canonical_smiles",
        "standard_inchi",
        "standard_inchi_key",
    ]
    return load_parquet_to_table(
        connection, parquet_path, "bronze", "compound_structures", columns
    )


def run_load(input_dir=None):
    if input_dir is None:
        input_dir = DEFAULT_INPUT_DIR

    connection = get_connection()

    results = {
        "chembl_id_lookup": load_chembl_id_lookup(connection, input_dir),
        "molecule_dictionary": load_molecule_dictionary(
            connection, input_dir
        ),
        "compound_properties": load_compound_properties(
            connection, input_dir
        ),
        "compound_structures": load_compound_structures(
            connection, input_dir
        ),
    }

    connection.close()
    return results


if __name__ == "__main__":
    results = run_load()

    for table, row_count in results.items():
        print(f"{table}: {row_count} rows loaded")

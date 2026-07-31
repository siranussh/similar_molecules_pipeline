import io
import os
import time

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
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
        options="-c statement_timeout=600000",
    )


def load_parquet_to_table(
    connection, parquet_path, schema, table, columns,
    int_columns=None, batch_size=1000000, max_retries=3,
):
    cursor = connection.cursor()
    cursor.execute(f"TRUNCATE TABLE {schema}.{table}")
    connection.commit()

    column_list = ", ".join(columns)
    copy_sql = (
        f"COPY {schema}.{table} ({column_list}) "
        f"FROM STDIN WITH (FORMAT csv, NULL '')"
    )

    parquet_file = pq.ParquetFile(parquet_path)
    total_rows = 0

    for batch_num, batch in enumerate(parquet_file.iter_batches(
        batch_size=batch_size, columns=columns
    )):
        batch_start = time.time()
        dataframe = batch.to_pandas()

        if int_columns is not None:
            for column in int_columns:
                dataframe[column] = dataframe[column].astype("Int64")

        buffer = io.StringIO()
        dataframe.to_csv(buffer, index=False, header=False)

        print(
            f"{table} batch {batch_num}: starting, {len(dataframe)} rows"
        )

        for attempt in range(max_retries):
            try:
                buffer.seek(0)
                cursor.copy_expert(copy_sql, buffer)
                connection.commit()
                break
            except psycopg2.OperationalError as error:
                print(
                    f"{table} batch {batch_num} attempt "
                    f"{attempt + 1} failed: {error}"
                )

                try:
                    connection.rollback()
                except psycopg2.OperationalError:
                    pass

                try:
                    connection.close()
                except psycopg2.OperationalError:
                    pass

                if attempt == max_retries - 1:
                    raise

                print(
                    f"{table} batch {batch_num}: reconnecting "
                    "before retry"
                )
                time.sleep(5)
                connection = get_connection()
                cursor = connection.cursor()

        batch_duration = time.time() - batch_start
        print(
            f"{table} batch {batch_num}: finished in "
            f"{batch_duration:.1f}s"
        )

        total_rows += len(dataframe)

    cursor.close()

    return total_rows, connection


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
    # Long text columns (SMILES, InChI, InChIKey) make each row heavier
    # than the other tables, so this table uses a smaller batch size to
    # keep each COPY comfortably within the statement timeout.
    parquet_path = os.path.join(input_dir, "compound_structures.parquet")
    columns = [
        "molregno",
        "canonical_smiles",
        "standard_inchi",
        "standard_inchi_key",
    ]
    return load_parquet_to_table(
        connection,
        parquet_path,
        "bronze",
        "compound_structures",
        columns,
        batch_size=300000,
    )


def run_load(input_dir=None):
    if input_dir is None:
        input_dir = DEFAULT_INPUT_DIR

    connection = get_connection()
    results = {}

    results["chembl_id_lookup"], connection = load_chembl_id_lookup(
        connection, input_dir
    )
    results["molecule_dictionary"], connection = load_molecule_dictionary(
        connection, input_dir
    )
    results["compound_properties"], connection = load_compound_properties(
        connection, input_dir
    )
    results["compound_structures"], connection = load_compound_structures(
        connection, input_dir
    )

    connection.close()
    return results


if __name__ == "__main__":
    results = run_load()

    for table, row_count in results.items():
        print(f"{table}: {row_count} rows loaded")

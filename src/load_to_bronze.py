import io
import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    database = os.environ["DB_NAME"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]

    return psycopg2.connect(
        host=host, port=port, dbname=database, user=user, password=password
    )


def load_dataframe_to_table(
    connection, dataframe, schema, table, columns, int_columns=None
):
    dataframe = dataframe[columns].copy()

    if int_columns is not None:
        for column in int_columns:
            dataframe[column] = dataframe[column].astype("Int64")

    buffer = io.StringIO()
    dataframe.to_csv(buffer, index=False, header=False)
    buffer.seek(0)

    cursor = connection.cursor()
    cursor.execute(f"TRUNCATE TABLE {schema}.{table}")

    column_list = ", ".join(columns)
    copy_sql = (
        f"COPY {schema}.{table} ({column_list}) "
        f"FROM STDIN WITH (FORMAT csv, NULL '')"
    )
    cursor.copy_expert(copy_sql, buffer)

    connection.commit()
    cursor.close()

    return len(dataframe)


def load_chembl_id_lookup(connection, input_dir):
    dataframe = pd.read_parquet(
        os.path.join(input_dir, "chembl_id_lookup.parquet")
    )
    columns = ["chembl_id", "entity_type", "entity_id", "status"]
    return load_dataframe_to_table(
        connection,
        dataframe,
        "bronze",
        "chembl_id_lookup",
        columns,
        int_columns=["entity_id"],
    )


def load_molecule_dictionary(connection, input_dir):
    dataframe = pd.read_parquet(
        os.path.join(input_dir, "molecule_dictionary.parquet")
    )
    columns = [
        "molregno",
        "chembl_id",
        "pref_name",
        "molecule_type",
        "max_phase",
        "therapeutic_flag",
        "withdrawn_flag",
    ]
    return load_dataframe_to_table(
        connection,
        dataframe,
        "bronze",
        "molecule_dictionary",
        columns,
        int_columns=["therapeutic_flag", "withdrawn_flag"],
    )


def load_compound_properties(connection, input_dir):
    dataframe = pd.read_parquet(
        os.path.join(input_dir, "compound_properties.parquet")
    )
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
    return load_dataframe_to_table(
        connection,
        dataframe,
        "bronze",
        "compound_properties",
        columns,
        int_columns=["hba", "hbd", "aromatic_rings", "heavy_atoms"],
    )


def load_compound_structures(connection, input_dir):
    dataframe = pd.read_parquet(
        os.path.join(input_dir, "compound_structures.parquet")
    )
    columns = [
        "molregno",
        "canonical_smiles",
        "standard_inchi",
        "standard_inchi_key",
    ]
    return load_dataframe_to_table(
        connection, dataframe, "bronze", "compound_structures", columns
    )


def run_load(input_dir="ingested_data"):
    connection = get_connection()

    results = {
        "chembl_id_lookup": load_chembl_id_lookup(connection, input_dir),
        "molecule_dictionary": load_molecule_dictionary(connection, input_dir),
        "compound_properties": load_compound_properties(connection, input_dir),
        "compound_structures": load_compound_structures(connection, input_dir),
    }

    connection.close()
    return results


if __name__ == "__main__":
    results = run_load()

    for table, row_count in results.items():
        print(f"{table}: {row_count} rows loaded")

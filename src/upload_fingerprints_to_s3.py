import os
import time

import pandas as pd
import psycopg2
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv

from fingerprints import compute_morgan_fingerprint
from s3_upload import upload_file

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


def fetch_structures_batch(connection, offset, batch_size):
    query = (
        "SELECT md.chembl_id, cs.canonical_smiles "
        "FROM bronze.molecule_dictionary md "
        "JOIN bronze.compound_structures cs "
        "ON md.molregno = cs.molregno "
        "WHERE cs.canonical_smiles IS NOT NULL "
        "ORDER BY md.chembl_id "
        "LIMIT %s OFFSET %s"
    )

    cursor = connection.cursor()
    cursor.execute(query, (batch_size, offset))
    rows = cursor.fetchall()
    cursor.close()

    return rows


def fingerprint_batch(structures):
    chembl_ids = []
    on_bits_list = []
    failed_count = 0

    for chembl_id, smiles in structures:
        fingerprint = compute_morgan_fingerprint(smiles)

        if fingerprint is None:
            failed_count += 1
        else:
            on_bits = list(fingerprint.GetOnBits())
            chembl_ids.append(chembl_id)
            on_bits_list.append(on_bits)

    dataframe = pd.DataFrame({
        "chembl_id": chembl_ids,
        "fingerprint_on_bits": on_bits_list,
    })

    return dataframe, failed_count


def run_fingerprint_and_save(
    connection, local_path, batch_size=200000
):
    offset = 0
    total_written = 0
    total_failed = 0
    writer = None

    while True:
        structures = fetch_structures_batch(connection, offset, batch_size)

        if len(structures) == 0:
            break

        dataframe, failed_count = fingerprint_batch(structures)
        total_failed += failed_count

        table = pa.Table.from_pandas(dataframe, preserve_index=False)

        if writer is None:
            writer = pq.ParquetWriter(local_path, table.schema)

        writer.write_table(table)
        total_written += len(dataframe)

        offset += batch_size

    if writer is not None:
        writer.close()

    return total_written, total_failed


if __name__ == "__main__":
    connection = get_connection()

    local_path = "fingerprints.parquet"

    process_start = time.perf_counter()
    total_written, total_failed = run_fingerprint_and_save(
        connection, local_path
    )
    process_elapsed = time.perf_counter() - process_start
    print(f"Fingerprinted {total_written} molecules "
          f"({total_failed} failed) in {process_elapsed:.2f}s.")

    connection.close()

    bucket = os.environ["S3_BUCKET"]
    subfolder = os.environ["S3_SUBFOLDER"]
    s3_key = f"{subfolder}/fingerprints.parquet"

    upload_start = time.perf_counter()
    uploaded_uri = upload_file(local_path, bucket, s3_key)
    upload_elapsed = time.perf_counter() - upload_start
    print(f"Uploaded to {uploaded_uri} in {upload_elapsed:.2f}s.")

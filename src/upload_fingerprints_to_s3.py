import os
import time

import pandas as pd
import psycopg2
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


def fetch_structures(connection, limit=None):
    query = (
        "SELECT md.chembl_id, cs.canonical_smiles "
        "FROM bronze.molecule_dictionary md "
        "JOIN bronze.compound_structures cs "
        "ON md.molregno = cs.molregno "
        "WHERE cs.canonical_smiles IS NOT NULL "
        "ORDER BY md.chembl_id"
    )

    if limit is not None:
        query += f" LIMIT {limit}"

    cursor = connection.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()

    return rows


def fingerprint_and_collect(structures):
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


def save_and_upload(dataframe, local_path, bucket, s3_key):
    dataframe.to_parquet(local_path, index=False)
    uploaded_uri = upload_file(local_path, bucket, s3_key)
    return uploaded_uri


if __name__ == "__main__":
    connection = get_connection()

    fetch_start = time.perf_counter()
    structures = fetch_structures(connection, limit=None)
    fetch_elapsed = time.perf_counter() - fetch_start
    print(f"Fetched {len(structures)} structures in {fetch_elapsed:.2f}s.")

    fingerprint_start = time.perf_counter()
    dataframe, failed_count = fingerprint_and_collect(structures)
    fingerprint_elapsed = time.perf_counter() - fingerprint_start
    print(f"Fingerprinted {len(dataframe)} molecules "
          f"({failed_count} failed) in {fingerprint_elapsed:.2f}s.")

    connection.close()

    local_path = "fingerprints.parquet"
    bucket = os.environ["S3_BUCKET"]
    subfolder = os.environ["S3_SUBFOLDER"]
    s3_key = f"{subfolder}/fingerprints.parquet"

    upload_start = time.perf_counter()
    uploaded_uri = save_and_upload(dataframe, local_path, bucket, s3_key)
    upload_elapsed = time.perf_counter() - upload_start
    print(f"Saved and uploaded to {uploaded_uri} in {upload_elapsed:.2f}s.")

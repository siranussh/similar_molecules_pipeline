import os
import time

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from rdkit import DataStructs

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


def fingerprint_structures(structures):
    fingerprinted = []
    failed_count = 0

    for chembl_id, smiles in structures:
        fingerprint = compute_morgan_fingerprint(smiles)

        if fingerprint is None:
            failed_count += 1
        else:
            fingerprinted.append((chembl_id, fingerprint))

    return fingerprinted, failed_count


def select_source_molecules(fingerprinted, count=100):
    return fingerprinted[:count]


def compute_full_similarity_for_source(source_id, source_fp, fingerprinted):
    target_ids = []
    scores = []

    for target_id, target_fp in fingerprinted:
        if target_id == source_id:
            continue

        similarity = DataStructs.TanimotoSimilarity(source_fp, target_fp)
        target_ids.append(target_id)
        scores.append(similarity)

    dataframe = pd.DataFrame({
        "target_chembl_id": target_ids,
        "similarity_score": scores,
    })

    return dataframe


def save_and_upload_source_table(
    dataframe, source_id, bucket, subfolder, local_dir="full_similarity"
):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    local_path = os.path.join(local_dir, f"{source_id}.parquet")
    dataframe.to_parquet(local_path, index=False)

    s3_key = f"{subfolder}/full_similarity/{source_id}.parquet"
    uploaded_uri = upload_file(local_path, bucket, s3_key)

    os.remove(local_path)

    return uploaded_uri


if __name__ == "__main__":
    connection = get_connection()

    fetch_start = time.perf_counter()
    structures = fetch_structures(connection, limit=None)
    fetch_elapsed = time.perf_counter() - fetch_start
    print(f"Fetched {len(structures)} structures in {fetch_elapsed:.2f}s.")

    fingerprint_start = time.perf_counter()
    fingerprinted, failed_count = fingerprint_structures(structures)
    fingerprint_elapsed = time.perf_counter() - fingerprint_start
    print(f"Fingerprinted {len(fingerprinted)} molecules "
          f"({failed_count} failed) in {fingerprint_elapsed:.2f}s.")

    source_molecules = select_source_molecules(fingerprinted, count=100)
    print(f"Selected {len(source_molecules)} source molecules.")

    connection.close()

    bucket = os.environ["S3_BUCKET"]
    subfolder = os.environ["S3_SUBFOLDER"]

    for source_id, source_fp in source_molecules:
        compute_start = time.perf_counter()
        dataframe = compute_full_similarity_for_source(
            source_id, source_fp, fingerprinted
        )
        compute_elapsed = time.perf_counter() - compute_start

        uploaded_uri = save_and_upload_source_table(
            dataframe, source_id, bucket, subfolder
        )
        print(f"{source_id}: {len(dataframe)} rows computed in "
              f"{compute_elapsed:.2f}s, uploaded to {uploaded_uri}")

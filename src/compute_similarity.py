import os
import time

import psycopg2
from dotenv import load_dotenv
from rdkit import DataStructs

from fingerprints import compute_morgan_fingerprint

load_dotenv()


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


def compute_top10_for_source(source_id, source_fp, fingerprinted):
    scored = []

    for target_id, target_fp in fingerprinted:
        if target_id == source_id:
            continue

        similarity = DataStructs.TanimotoSimilarity(source_fp, target_fp)
        scored.append((target_id, similarity))

    scored.sort(key=lambda pair: pair[1], reverse=True)

    top10 = scored[:10]

    if len(top10) < 10:
        return [
            (target_id, score, False) for target_id, score in top10
        ]

    boundary_score = top10[9][1]
    has_ties_beyond_top10 = any(
        score == boundary_score for target_id, score in scored[10:]
    )

    result = []
    for target_id, score in top10:
        is_boundary_row = (
            has_ties_beyond_top10 and score == boundary_score
        )
        result.append((target_id, score, is_boundary_row))

    return result


def compute_all_similarities(source_molecules, fingerprinted):
    all_results = []
    total = len(source_molecules)

    for index, (source_id, source_fp) in enumerate(source_molecules, 1):
        source_start = time.perf_counter()

        top10 = compute_top10_for_source(source_id, source_fp, fingerprinted)

        for target_id, score, is_boundary_row in top10:
            all_results.append((source_id, target_id, score, is_boundary_row))

        source_elapsed = time.perf_counter() - source_start
        print(
            f"source {index}/{total}: {source_id} done "
            f"in {source_elapsed:.2f}s"
        )

    return all_results


def write_to_fact_similarity(connection, results, max_retries=3):
    for attempt in range(max_retries):
        try:
            cursor = connection.cursor()
            cursor.execute("TRUNCATE TABLE gold.fact_similarity")

            insert_sql = (
                "INSERT INTO gold.fact_similarity "
                "(source_chembl_id, target_chembl_id, similarity_score, "
                "has_duplicates_of_last_largest_score) "
                "VALUES (%s, %s, %s, %s)"
            )
            cursor.executemany(insert_sql, results)

            connection.commit()
            cursor.close()

            return len(results), connection
        except psycopg2.OperationalError as error:
            print(f"write_to_fact_similarity attempt "
                  f"{attempt + 1} failed: {error}")

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

            print("write_to_fact_similarity: reconnecting before retry")
            time.sleep(5)
            connection = get_connection()


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

    similarity_start = time.perf_counter()
    results = compute_all_similarities(source_molecules, fingerprinted)
    similarity_elapsed = time.perf_counter() - similarity_start
    print(f"Computed {len(results)} similarity rows "
          f"in {similarity_elapsed:.2f}s.")

    write_count, connection = write_to_fact_similarity(connection, results)
    print(f"Wrote {write_count} rows to gold.fact_similarity.")

    connection.close()

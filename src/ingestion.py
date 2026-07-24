import os

import chembl_downloader


def ingest_chembl_id_lookup(limit=None):
    query = (
        "SELECT chembl_id, entity_type, entity_id, status "
        "FROM chembl_id_lookup"
    )

    if limit is not None:
        query += f" LIMIT {limit}"

    return chembl_downloader.query(query)


def ingest_molecule_dictionary(limit=None):
    query = (
        "SELECT molregno, chembl_id, pref_name, molecule_type, "
        "max_phase, therapeutic_flag, withdrawn_flag "
        "FROM molecule_dictionary"
    )

    if limit is not None:
        query += f" LIMIT {limit}"

    return chembl_downloader.query(query)


def ingest_compound_properties(limit=None):
    query = (
        "SELECT molregno, mw_freebase, full_mwt, alogp, hba, hbd, psa, "
        "aromatic_rings, heavy_atoms, qed_weighted "
        "FROM compound_properties"
    )

    if limit is not None:
        query += f" LIMIT {limit}"

    return chembl_downloader.query(query)


def ingest_compound_structures(limit=None):
    query = (
        "SELECT molregno, canonical_smiles, standard_inchi, "
        "standard_inchi_key "
        "FROM compound_structures "
        "WHERE canonical_smiles IS NOT NULL"
    )

    if limit is not None:
        query += f" LIMIT {limit}"

    return chembl_downloader.query(query)


def save_to_parquet(dataframe, output_dir, filename):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_path = os.path.join(output_dir, filename)
    dataframe.to_parquet(output_path, index=False)
    return output_path


def run_ingestion(output_dir="ingested_data", limit=None):
    id_lookup = ingest_chembl_id_lookup(limit)
    molecule_dict = ingest_molecule_dictionary(limit)
    properties = ingest_compound_properties(limit)
    structures = ingest_compound_structures(limit)

    tables = {
        "chembl_id_lookup.parquet": id_lookup,
        "molecule_dictionary.parquet": molecule_dict,
        "compound_properties.parquet": properties,
        "compound_structures.parquet": structures,
    }

    saved_paths = {}

    for filename, dataframe in tables.items():
        path = save_to_parquet(dataframe, output_dir, filename)
        saved_paths[filename] = (path, len(dataframe))

    return saved_paths


if __name__ == "__main__":
    results = run_ingestion(limit=None)

    for filename, (path, row_count) in results.items():
        print(f"{filename}: {row_count} rows saved to {path}")

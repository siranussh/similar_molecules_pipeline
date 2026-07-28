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
    saved_paths = {}

    id_lookup = ingest_chembl_id_lookup(limit)
    path = save_to_parquet(id_lookup, output_dir, "chembl_id_lookup.parquet")
    saved_paths["chembl_id_lookup.parquet"] = (path, len(id_lookup))
    del id_lookup

    molecule_dict = ingest_molecule_dictionary(limit)
    path = save_to_parquet(
        molecule_dict, output_dir, "molecule_dictionary.parquet"
    )
    saved_paths["molecule_dictionary.parquet"] = (path, len(molecule_dict))
    del molecule_dict

    properties = ingest_compound_properties(limit)
    path = save_to_parquet(
        properties, output_dir, "compound_properties.parquet"
    )
    saved_paths["compound_properties.parquet"] = (path, len(properties))
    del properties

    structures = ingest_compound_structures(limit)
    path = save_to_parquet(
        structures, output_dir, "compound_structures.parquet"
    )
    saved_paths["compound_structures.parquet"] = (path, len(structures))
    del structures

    return saved_paths


if __name__ == "__main__":
    results = run_ingestion(limit=None)

    for filename, (path, row_count) in results.items():
        print(f"{filename}: {row_count} rows saved to {path}")

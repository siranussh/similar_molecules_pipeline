import chembl_downloader


def pull_sample(limit=2000):
    """
    Download/use the cached ChEMBL SQLite database and pull a small
    sample of molecule_chembl_id + canonical_smiles pairs.
    """
    query = f"""
        SELECT
            md.chembl_id,
            cs.canonical_smiles
        FROM molecule_dictionary md
        JOIN compound_structures cs
            ON md.molregno = cs.molregno
        WHERE cs.canonical_smiles IS NOT NULL
        LIMIT {limit}
    """

    dataframe = chembl_downloader.query(query)
    return dataframe


if __name__ == "__main__":
    sample = pull_sample(limit=2000)
    sample.to_csv("chembl_sample.csv", index=False)
    print(f"Saved {len(sample)} molecules to chembl_sample.csv")
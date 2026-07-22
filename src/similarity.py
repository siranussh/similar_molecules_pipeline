from rdkit import DataStructs

from fingerprints import compute_morgan_fingerprint


def compute_tanimoto_similarity(fingerprint_a, fingerprint_b):
    similarity = DataStructs.TanimotoSimilarity(fingerprint_a, fingerprint_b)
    return similarity


if __name__ == "__main__":
    molecules = {
        "aspirin": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "salicylic_acid": "OC(=O)C1=CC=CC=C1O",
        "caffeine": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    }

    fingerprints = {}

    for name, smiles in molecules.items():
        fingerprint = compute_morgan_fingerprint(smiles)

        if fingerprint is None:
            print(f"Failed to parse SMILES for {name}.")
        else:
            fingerprints[name] = fingerprint

    pairs = [
        ("aspirin", "salicylic_acid"),
        ("aspirin", "caffeine"),
        ("salicylic_acid", "caffeine"),
    ]

    for name_a, name_b in pairs:
        similarity = compute_tanimoto_similarity(
            fingerprints[name_a], fingerprints[name_b]
        )
        print(f"{name_a} vs {name_b}: {similarity:.4f}")

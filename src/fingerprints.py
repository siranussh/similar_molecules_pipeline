from rdkit import Chem
from rdkit.Chem import rdFingerprintGenerator


def compute_morgan_fingerprint(smiles, radius=2, n_bits=2048):
    if smiles is None or smiles.strip() == "":
        return None

    molecule = Chem.MolFromSmiles(smiles)

    if molecule is None:
        return None
    else:
        generator = rdFingerprintGenerator.GetMorganGenerator(
            radius=radius, fpSize=n_bits
        )
        fingerprint = generator.GetFingerprint(molecule)
        return fingerprint


if __name__ == "__main__":
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"

    fingerprint = compute_morgan_fingerprint(aspirin_smiles)

    if fingerprint is None:
        print("Failed to parse SMILES.")
    else:
        print(f"SMILES: {aspirin_smiles}")
        print(f"Fingerprint length: {len(fingerprint)}")
        print(f"Number of bits set: {fingerprint.GetNumOnBits()}")

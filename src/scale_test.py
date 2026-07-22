import csv
import time

from rdkit import DataStructs

from fingerprints import compute_morgan_fingerprint


def load_molecules(csv_path):
   
    molecules = []

    with open(csv_path, newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            molecules.append((row["chembl_id"], row["canonical_smiles"]))

    return molecules


def fingerprint_all(molecules):
    fingerprints = []
    failed_count = 0

    for chembl_id, smiles in molecules:
        fingerprint = compute_morgan_fingerprint(smiles)

        if fingerprint is None:
            failed_count += 1
        else:
            fingerprints.append((chembl_id, fingerprint))

    return fingerprints, failed_count


if __name__ == "__main__":
    molecules = load_molecules("chembl_sample.csv")
    print(f"Loaded {len(molecules)} molecules from CSV.")

    fingerprint_start = time.perf_counter()
    fingerprints, failed_count = fingerprint_all(molecules)
    fingerprint_elapsed = time.perf_counter() - fingerprint_start

    print(f"Fingerprinted {len(fingerprints)} molecules "
          f"({failed_count} failed to parse) in {fingerprint_elapsed:.2f}s.")
    print(f"Average fingerprint time: "
          f"{(fingerprint_elapsed / len(fingerprints)) * 1000:.3f} ms/molecule.")

    source_id, source_fp = fingerprints[0]
    targets = fingerprints[1:]

    similarity_start = time.perf_counter()

    scored_targets = []
    for target_id, target_fp in targets:
        similarity = DataStructs.TanimotoSimilarity(source_fp, target_fp)
        scored_targets.append((target_id, similarity))

    similarity_elapsed = time.perf_counter() - similarity_start

    print(f"\nCompared source {source_id} against {len(targets)} "
          f"targets in {similarity_elapsed:.4f}s.")
    print(f"Average comparison time: "
          f"{(similarity_elapsed / len(targets)) * 1e6:.2f} microseconds/comparison.")

    scored_targets.sort(key=lambda pair: pair[1], reverse=True)

    print(f"\nTop 5 most similar to {source_id}:")
    for target_id, similarity in scored_targets[:5]:
        print(f"  {target_id}: {similarity:.4f}")

import pandas as pd

id_lookup = pd.read_parquet("test_ingestion/chembl_id_lookup.parquet")
molecule_dict = pd.read_parquet("test_ingestion/molecule_dictionary.parquet")
properties = pd.read_parquet("test_ingestion/compound_properties.parquet")
structures = pd.read_parquet("test_ingestion/compound_structures.parquet")

print("chembl_id_lookup:")
print(id_lookup.head())
print()

print("molecule_dictionary:")
print(molecule_dict.head())
print()

print("compound_properties:")
print(properties.head())
print()

print("compound_structures:")
print(structures.head())

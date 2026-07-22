from ingestion import run_ingestion

results = run_ingestion(output_dir="ingested_data", limit=None)

for filename, (path, row_count) in results.items():
    print(f"{filename}: {row_count} rows saved to {path}")

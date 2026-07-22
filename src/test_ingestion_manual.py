from ingestion import run_ingestion

results = run_ingestion(output_dir="test_ingestion", limit=100)
print(results)
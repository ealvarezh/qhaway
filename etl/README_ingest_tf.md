# Ingest TF report helper

This folder contains `ingest_tf.py`, a conservative helper that copies files
referenced in a `tf_report.json` into the repository so you can inspect and
integrate them into the existing ETL.

Quick start (from workspace root):

```bash
python etl/ingest_tf.py --report path/to/tf_report.json --target data/processed/external_tf
```

Options:
- `--dry-run` : show what would be copied without performing any file writes.

Next steps after running:
- Inspect `data/processed/external_tf/mapping.json` to see copied files.
- If Parquet files match the schemas expected by the repo ETL, run `etl/preaggregate.py` or adapt the files into `data/processed`.
- If you want, I can implement automatic schema mapping and a small pipeline to convert these inputs into `taxa_enriched.parquet`, `photos.parquet` and `agg/species_list.parquet` used by the backend.

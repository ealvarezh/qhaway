#!/usr/bin/env python3
"""
Simple ingestion helper for the TF report produced by `etl/import_tf.py`.

What it does:
- Reads a `tf_report.json` (default: workspace root) and copies referenced
  Parquet and JSON files into the repo under `data/processed/external_tf/`.
- Produces `mapping.json` summarizing copied files.

Usage:
  python etl/ingest_tf.py --report PATH/TO/tf_report.json --target data/processed/external_tf

Options:
  --dry-run   : don't actually copy files, only print actions
  --report    : path to tf_report.json
  --target    : target directory inside repo where files will be copied

This is intentionally conservative: it only copies files and emits a mapping.
Further transforms (schema conversion, running `preaggregate.py`) are left
for the next steps once you confirm the copied inputs.
"""
import argparse
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime


def copy_file(src: Path, dst: Path, dry_run: bool):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        logging.info(f"[DRY] Copy {src} -> {dst}")
        return True
    try:
        shutil.copy2(src, dst)
        logging.info(f"Copied {src} -> {dst}")
        return True
    except Exception as e:
        logging.error(f"Failed to copy {src} -> {dst}: {e}")
        return False


def safe_relpath(src: Path, base_root: str):
    try:
        return src.relative_to(Path(base_root))
    except Exception:
        # fallback to name only
        return Path(src.name)


def main():
    parser = argparse.ArgumentParser(description="Ingest TF report files into repo structure")
    parser.add_argument("--report", default="tf_report.json", help="Path to tf_report.json")
    parser.add_argument("--target", default="data/processed/external_tf", help="Target directory in repo")
    parser.add_argument("--dry-run", action="store_true", help="Don't copy files, only show actions")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    report_path = Path(args.report)
    if not report_path.exists():
        logging.error(f"Report not found: {report_path}")
        return

    with report_path.open("r", encoding="utf-8") as f:
        report = json.load(f)

    target_base = Path(args.target)
    mapping = {
        "report": str(report_path.resolve()),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "root": report.get("root"),
        "copied": [],
        "skipped": [],
    }

    root = report.get("root")

    # handle parquets
    for p in report.get("parquets", []):
        src = Path(p.get("path"))
        rel = safe_relpath(src, root) if root else Path(src.name)
        dst = target_base / "parquets" / rel
        if src.exists():
            ok = copy_file(src, dst, args.dry_run)
            entry = {"src": str(src), "dst": str(dst), "ok": ok}
            mapping["copied"].append(entry) if ok else mapping["skipped"].append(entry)
        else:
            mapping["skipped"].append({"src": str(src), "reason": "missing"})

    # handle jsons
    for j in report.get("jsons", []):
        src = Path(j.get("path"))
        rel = safe_relpath(src, root) if root else Path(src.name)
        dst = target_base / "jsons" / rel
        if src.exists():
            ok = copy_file(src, dst, args.dry_run)
            entry = {"src": str(src), "dst": str(dst), "ok": ok}
            mapping["copied"].append(entry) if ok else mapping["skipped"].append(entry)
        else:
            mapping["skipped"].append({"src": str(src), "reason": "missing"})

    # handle embeddings files (npz/npy) and others
    for e in report.get("embeddings_files", []) if isinstance(report.get("embeddings_files"), list) else []:
        src = Path(e.get("path"))
        rel = safe_relpath(src, root) if root else Path(src.name)
        dst = target_base / "embeddings" / rel
        if src.exists():
            ok = copy_file(src, dst, args.dry_run)
            entry = {"src": str(src), "dst": str(dst), "ok": ok}
            mapping["copied"].append(entry) if ok else mapping["skipped"].append(entry)
        else:
            mapping["skipped"].append({"src": str(src), "reason": "missing"})

    # write mapping
    mapping_path = target_base / "mapping.json"
    target_base.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        logging.info(f"[DRY] Would write mapping to {mapping_path}")
    else:
        with mapping_path.open("w", encoding="utf-8") as mf:
            json.dump(mapping, mf, indent=2, ensure_ascii=False)
        logging.info(f"Mapping written to {mapping_path}")

    logging.info("Done. Review mapping.json and run further ETL steps as needed.")


if __name__ == "__main__":
    main()

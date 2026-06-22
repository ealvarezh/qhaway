#!/usr/bin/env python3
"""
Construye un `species_list.parquet` simple a partir de los JSON copiados
en `data/processed/external_tf/jsons/...` para uso local y pruebas.

Salida: `data/processed/external_tf/species_list.parquet`
"""
from pathlib import Path
import json
import pandas as pd


ROOT = Path('data/processed/external_tf')
JSON_ROOT = ROOT / 'jsons'
OUT = ROOT / 'species_list.parquet'


def load_json_files(root: Path):
    for p in root.rglob('*.json'):
        yield p


def extract_rows(p: Path):
    try:
        obj = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return []

    rows = []
    # If top-level is dict with named entries
    if isinstance(obj, dict):
        # common knowledge_base structure: mapping species_name -> metadata
        # or a list under keys
        # try detect list values
        if all(isinstance(v, dict) for v in obj.values()):
            for k, v in obj.items():
                row = {
                    'external_id': v.get('id') or k,
                    'name': v.get('species') or v.get('name') or k,
                    'family': v.get('family'),
                    'order': v.get('order'),
                    'image_url': (v.get('image_url') or (v.get('image_urls') or [None])[0]),
                    'dataset_records': v.get('dataset_records') or v.get('dataset_records', None),
                    'subrepresented': v.get('subrepresented') if 'subrepresented' in v else None,
                    'source_file': str(p)
                }
                rows.append(row)
        else:
            # maybe it's a list under a top key
            for k in ['preview', 'data', 'results', 'items']:
                if k in obj and isinstance(obj[k], list):
                    for v in obj[k]:
                        row = {
                            'external_id': v.get('id') or v.get('species'),
                            'name': v.get('name') or v.get('species'),
                            'family': v.get('family'),
                            'order': v.get('order'),
                            'image_url': (v.get('image_url') or (v.get('image_urls') or [None])[0]),
                            'dataset_records': v.get('dataset_records'),
                            'subrepresented': v.get('subrepresented'),
                            'source_file': str(p)
                        }
                        rows.append(row)
    elif isinstance(obj, list):
        for v in obj:
            if not isinstance(v, dict):
                continue
            row = {
                'external_id': v.get('id') or v.get('species'),
                'name': v.get('name') or v.get('species'),
                'family': v.get('family'),
                'order': v.get('order'),
                'image_url': (v.get('image_url') or (v.get('image_urls') or [None])[0]),
                'dataset_records': v.get('dataset_records'),
                'subrepresented': v.get('subrepresented'),
                'source_file': str(p)
            }
            rows.append(row)

    return rows


def run():
    ROOT.mkdir(parents=True, exist_ok=True)
    if not JSON_ROOT.exists():
        print(f"No JSONs found under {JSON_ROOT}. Run ingestion first.")
        return

    rows = []
    for p in load_json_files(JSON_ROOT):
        rows.extend(extract_rows(p))

    if not rows:
        print("No species rows extracted from JSONs.")
        return

    df = pd.DataFrame(rows)
    # dedupe by name
    df.drop_duplicates(subset=['name'], inplace=True)

    # assign a synthetic taxon_id (negative to avoid collision)
    df = df.reset_index(drop=True)
    df['taxon_id'] = -1 - df.index.astype('int32')

    # normalize columns expected by frontend/backend species_list (partial)
    out_cols = ['taxon_id', 'name', 'family', 'order', 'image_url', 'dataset_records', 'subrepresented', 'source_file']
    for c in out_cols:
        if c not in df.columns:
            df[c] = None

    df = df[out_cols]

    df.to_parquet(OUT, index=False, compression='zstd')
    print(f"Wrote {OUT} ({len(df)} rows)")


if __name__ == '__main__':
    run()

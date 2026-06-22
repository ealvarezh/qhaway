#!/usr/bin/env python3
"""
Analiza los Parquet de embeddings en `data/processed/external_tf/parquets`.
Genera `data/processed/external_tf/embeddings_report.json` con estadísticas.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

PARQUET_ROOT = Path('data/processed/external_tf/parquets')
OUT = Path('data/processed/external_tf/embeddings_report.json')


def inspect_parquet(p: Path):
    try:
        df = pd.read_parquet(p, columns=None)
    except Exception as e:
        return {'path': str(p), 'error': str(e)}

    info = {'path': str(p), 'rows': len(df), 'columns': list(df.columns)}
    if 'embedding' in df.columns:
        # attempt to sample up to 100 vectors
        sample = df['embedding'].dropna().head(100).tolist()
        if len(sample) == 0:
            info['embedding'] = {'present': True, 'sample_count': 0}
        else:
            arr = np.vstack([np.array(x, dtype=float) for x in sample])
            dims = arr.shape[1]
            norms = np.linalg.norm(arr, axis=1)
            info['embedding'] = {
                'present': True,
                'sample_count': len(sample),
                'dim': int(dims),
                'norm_mean': float(np.mean(norms)),
                'norm_std': float(np.std(norms)),
                'norm_min': float(np.min(norms)),
                'norm_max': float(np.max(norms)),
            }
    return info


def run():
    results = []
    if not PARQUET_ROOT.exists():
        print(f"No parquet folder: {PARQUET_ROOT}")
        return

    total_vectors = 0
    for p in PARQUET_ROOT.rglob('*.parquet'):
        info = inspect_parquet(p)
        results.append(info)
        if 'embedding' in info.get('columns', []) and info.get('rows'):
            total_vectors += info.get('rows', 0)

    report = {
        'generated': True,
        'files': results,
        'total_files': len(results),
        'estimated_total_vectors': total_vectors,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Wrote {OUT}")


if __name__ == '__main__':
    run()

"""
Inspección de un directorio TF externo (E:\\TF1_bichos\\tf).

Genera un informe JSON con:
 - Archivos Parquet encontrados y su esquema/filas de ejemplo
 - Archivos JSON y muestra de keys
 - Ficheros de embeddings (npy/npz) y su forma
 - Conteo de imágenes en subcarpetas

Uso:
  python etl/import_tf.py --tf-root "E:\\TF1_bichos\\tf" --out report_tf.json

No modifica archivos; solo lee metadatos y muestras pequeñas.
"""

import argparse
import json
import os
from pathlib import Path
import traceback

import pyarrow.parquet as pq
import numpy as np
import datetime


def analyze_parquet(path: Path):
    try:
        pf = pq.ParquetFile(str(path))
        schema = str(pf.schema)
        num_row_groups = pf.num_row_groups
        # Try to read a small sample (first row group)
        try:
            tbl = pf.read_row_groups([0]) if num_row_groups > 0 else pf.read()
            sample = tbl.to_pandas().head(5).to_dict(orient='records')
        except Exception:
            sample = []
        return {'path': str(path), 'schema': schema, 'num_row_groups': num_row_groups, 'sample_rows': sample}
    except Exception as e:
        return {'path': str(path), 'error': repr(e), 'trace': traceback.format_exc()}


def analyze_json(path: Path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            obj = json.load(f)
        if isinstance(obj, dict):
            keys = list(obj.keys())[:20]
            preview = {k: obj[k] for k in keys}
        elif isinstance(obj, list):
            preview = obj[:5]
            keys = None
        else:
            preview = str(obj)[:200]
            keys = None
        return {'path': str(path), 'type': 'json', 'keys_sample': keys, 'preview': preview}
    except Exception as e:
        return {'path': str(path), 'error': repr(e)}


def analyze_embeddings(path: Path):
    try:
        if path.suffix == '.npy':
            arr = np.load(str(path), mmap_mode='r')
            shape = getattr(arr, 'shape', None)
            dtype = str(arr.dtype) if hasattr(arr, 'dtype') else None
            return {'path': str(path), 'format': 'npy', 'shape': shape, 'dtype': dtype}
        if path.suffix == '.npz':
            with np.load(str(path), mmap_mode='r') as data:
                keys = list(data.keys())
                shapes = {k: data[k].shape for k in keys}
            return {'path': str(path), 'format': 'npz', 'keys': keys, 'shapes': shapes}
        return {'path': str(path), 'note': 'unknown embedding filetype'}
    except Exception as e:
        return {'path': str(path), 'error': repr(e)}


def count_images_in_dir(path: Path):
    img_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}
    counts = {}
    for root, dirs, files in os.walk(path):
        c = sum(1 for f in files if Path(f).suffix.lower() in img_exts)
        if c:
            counts[root] = c
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tf-root', required=True, help='Ruta al directorio TF (ej: E:\\\\TF1_bichos\\\\tf)')
    parser.add_argument('--out', default='report_tf.json', help='Archivo JSON de salida')
    args = parser.parse_args()

    root = Path(args.tf_root)
    if not root.exists():
        print(f"Ruta no encontrada: {root}")
        return

    report = {'root': str(root), 'parquets': [], 'jsons': [], 'embeddings': [], 'images_count': {}, 'other_files': []}

    for dirpath, dirnames, filenames in os.walk(root):
        pdir = Path(dirpath)
        for fn in filenames:
            f = pdir / fn
            suf = f.suffix.lower()
            if suf in {'.parquet'}:
                report['parquets'].append(analyze_parquet(f))
            elif suf in {'.json'}:
                report['jsons'].append(analyze_json(f))
            elif suf in {'.npy', '.npz'}:
                report['embeddings'].append(analyze_embeddings(f))
            elif suf in {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}:
                # images counted separately
                pass
            else:
                if suf in {'.csv', '.tsv', '.txt'}:
                    try:
                        report['other_files'].append({'path': str(f), 'size_bytes': f.stat().st_size})
                    except Exception:
                        report['other_files'].append({'path': str(f), 'size_bytes': None})

    report['images_count'] = count_images_in_dir(root)

    def make_json_safe(obj):
        # Recursively convert non-serializable objects to JSON-safe types
        if obj is None:
            return None
        if isinstance(obj, (str, bool, int, float)):
            return obj
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.ndarray,)):
            try:
                return obj.tolist()
            except Exception:
                return str(obj.shape)
        if isinstance(obj, (list, tuple)):
            return [make_json_safe(v) for v in obj]
        if isinstance(obj, dict):
            return {str(k): make_json_safe(v) for k, v in obj.items()}
        if isinstance(obj, bytes):
            try:
                return obj.decode('utf-8', errors='replace')
            except Exception:
                return str(obj)
        # pandas / pyarrow types -> try common conversions
        try:
            # datetime-like
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            if hasattr(obj, 'isoformat') and callable(obj.isoformat):
                return obj.isoformat()
        except Exception:
            pass
        # Fallback to string
        try:
            return str(obj)
        except Exception:
            return None

    safe_report = make_json_safe(report)
    with open(args.out, 'w', encoding='utf-8') as fo:
        json.dump(safe_report, fo, ensure_ascii=False, indent=2)

    print(f"Informe generado: {args.out}")


if __name__ == '__main__':
    main()

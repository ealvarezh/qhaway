"""API minimal para los datos externos copiados desde TF.

GET /api/external_species  — lista paginada desde `data/processed/external_tf/species_list.parquet`
GET /api/external_species/{taxon_id} — detalle
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi import File, UploadFile, Form
from fastapi.responses import JSONResponse
import pandas as pd
import json
from pathlib import Path
from PIL import Image
import io

from backend.services import vr_rag

router = APIRouter()

_DF = None
_PATH = Path('data/processed/external_tf/species_list.parquet')


def _load_df():
    global _DF
    if _DF is None:
        if not _PATH.exists():
            _DF = pd.DataFrame()
        else:
            _DF = pd.read_parquet(_PATH)
    return _DF


def _species_meta(name: str) -> dict:
    if not name:
        return {}

    df = _load_df()
    if df.empty:
        return {}

    match = df[df['name'].str.lower() == name.lower()]
    if match.empty:
        return {}

    row = match.iloc[0]
    return {
        'taxon_id': int(row['taxon_id']) if pd.notna(row.get('taxon_id')) else None,
        'family': row.get('family'),
        'order': row.get('order'),
        'image_url': row.get('image_url'),
        'dataset_records': int(row['dataset_records']) if pd.notna(row.get('dataset_records')) else None,
    }


def _augment_prediction(pred: dict) -> dict:
    pred = dict(pred)
    name = pred.get('name') or pred.get('target_species') or pred.get('species')
    if name:
        pred['name'] = name
        pred.update({k: v for k, v in _species_meta(name).items() if v is not None})
    return pred


@router.get("")
def list_external_species(
    q: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=200),
    sort_by: str = Query("name"),
):
    df = _load_df().copy()
    if df.empty:
        return JSONResponse({"page": page, "page_size": page_size, "total": 0, "data": []})

    if q:
        df = df[df['name'].str.contains(q, case=False, na=False)]

    sort_col = {'name': 'name', 'obs': 'dataset_records'}.get(sort_by, 'name')
    df = df.sort_values(sort_col, ascending=(sort_col == 'name'))

    total = len(df)
    start = (page - 1) * page_size
    page_df = df.iloc[start:start + page_size]

    records = json.loads(page_df.to_json(orient='records', force_ascii=False))

    return JSONResponse({"page": page, "page_size": page_size, "total": total, "data": records})


@router.get("/{taxon_id}")
def external_species_detail(taxon_id: int):
    df = _load_df()
    if df.empty:
        raise HTTPException(status_code=404, detail="external species data not found")

    row = df[df['taxon_id'] == int(taxon_id)]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"taxon_id {taxon_id} not found")
    result = json.loads(row.iloc[0].to_json(force_ascii=False))
    return JSONResponse(result)


@router.post("/predict")
async def predict_external_species(
    file: UploadFile = File(...),
    known_species: str = Form(None),
    family: str = Form(None),
):
    """Pipeline VR-RAG (igual a tf/big_data_project/src/test_vr_rag_insecta.py):

    Etapa 1 — ranking de la imagen subida contra embeddings de TEXTO
              (BioCLIP + CLIP ensemble) de las descripciones taxonómicas.
    Etapa 2 — re-ranking de los candidatos de la etapa 1 contra embeddings
              de IMÁGENES ancla (DINOv2) por especie.
    Etapa 3 — deliberación final: especie ganadora + nivel de confianza.
    """
    raw = await file.read()
    try:
        img = Image.open(io.BytesIO(raw)).convert('RGB')
    except Exception:
        raise HTTPException(status_code=400, detail="Archivo de imagen inválido")

    try:
        pipeline = vr_rag.run_pipeline(img)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fallo en el pipeline VR-RAG: {exc}")

    stage2 = [_augment_prediction(p) for p in pipeline['stage2']]
    result = {
        'source': 'vr_rag',
        'stage1': pipeline['stage1'][:10],
        'stage2': stage2,
        'stage3': pipeline['stage3'],
        'predictions': stage2,
    }

    if known_species and result['predictions']:
        top1_name = result['predictions'][0].get('name')
        result['known_species'] = known_species
        result['top1_is_known'] = bool(top1_name and top1_name.lower() == known_species.lower())

    return JSONResponse(result)

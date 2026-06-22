"""
GET /api/species       — lista paginada desde RAM (species_list)
GET /api/species/{id}  — detalle con LRU cache
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import json

from backend.dashboard.cache import AGG, ECO_H3, get_species
from backend.dashboard.filters import apply_taxa, apply_ecoregions

router = APIRouter()


@router.get("")
def list_species(
    kingdom:   str = Query(""),
    phylum:    str = Query(""),
    klass:     str = Query("", alias="class"),
    order:     str = Query(""),
    eco_ids:   str = Query(""),
    q:         str = Query(""),
    page:      int = Query(1,  ge=1),
    page_size: int = Query(24, ge=1, le=100),
    sort_by:   str = Query("obs"),
    grade:     str = Query("all"),
):
    df: pd.DataFrame = AGG["species_list"].copy()

    df = apply_taxa(df, kingdom, phylum, klass, order)
    df = apply_ecoregions(df, eco_ids, ECO_H3)
    if grade != "all":
        df = df[df["quality_grade"] == grade]
    if q:
        df = df[df["name"].str.contains(q, case=False, na=False)]

    sort_col = {"obs": "n_obs", "name": "name", "observers": "n_observers"}.get(sort_by, "n_obs")
    df = df.sort_values(sort_col, ascending=(sort_col == "name"))

    total = len(df)
    start = (page - 1) * page_size
    page_df = df.iloc[start:start + page_size]

    # to_json convierte NaN → null correctamente
    records = json.loads(page_df.to_json(orient="records"))

    return JSONResponse({
        "page":      page,
        "page_size": page_size,
        "total":     total,
        "data":      records,
    })


@router.get("/{taxon_id}")
def species_detail(taxon_id: int):
    try:
        result = get_species(taxon_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result.get("name") is None:
        raise HTTPException(status_code=404, detail=f"taxon_id {taxon_id} not found")

    return JSONResponse(result)
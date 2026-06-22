"""
GET /api/map/hex

Devuelve conteos por celda H3 para el mapa de densidad.
Lee desde AGG['hex_density'] (DataFrame en RAM) — sin tocar DuckDB.

Query params:
  resolution  3 | 5          (default: 3)
  kingdom     str | "all"    (default: all)
  year_min    int            (default: sin filtro)
  year_max    int            (default: sin filtro)
  metric      obs | species | observers  (default: obs)
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import pandas as pd

from backend.dashboard.cache import AGG, ECO_H3
from backend.dashboard.filters import apply_taxa, apply_ecoregions

router = APIRouter()

METRIC_COL = {
    "obs":       "n_obs",
    "species":   "n_species",
    "observers": "n_observers",
}

RESOLUTION_COL = {
    3: "h3_r3",
    5: "h3_r5",
}


@router.get("/hex")
def hex_density(
    resolution: int   = Query(3,     ge=3, le=5),
    kingdom:    str   = Query(""),
    phylum:     str   = Query(""),
    klass:      str   = Query("", alias="class"),
    order:      str   = Query(""),
    eco_ids:    str   = Query(""),
    year_min:   int   = Query(None),
    year_max:   int   = Query(None),
    metric:     str   = Query("obs"),
    grade:      str   = Query("all"),
):
    df: pd.DataFrame = AGG["hex_density"].copy()

    # Filtros
    df = apply_taxa(df, kingdom, phylum, klass, order)
    df = apply_ecoregions(df, eco_ids, ECO_H3)
    if grade != "all":
        df = df[df["quality_grade"] == grade]
    if year_min is not None:
        df = df[df["year"] >= year_min]
    if year_max is not None:
        df = df[df["year"] <= year_max]

    h3_col    = RESOLUTION_COL.get(resolution, "h3_r3")
    metric_col = METRIC_COL.get(metric, "n_obs")

    # Agrupar por celda H3 (puede haber varias filas por celda tras filtrar)
    grouped = (
        df.groupby(h3_col, dropna=True)
        .agg(
            n_obs       =("n_obs",       "sum"),
            n_species   =("n_species",   "sum"),
            n_observers =("n_observers", "sum"),
        )
        .reset_index()
        .rename(columns={h3_col: "h3"})
    )

    grouped["value"] = grouped[metric_col]

    # deck.gl espera una lista de {h3, value}
    records = grouped[["h3", "value"]].to_dict(orient="records")

    return JSONResponse({
        "resolution": resolution,
        "metric":     metric,
        "n_cells":    len(records),
        "data":       records,
    })
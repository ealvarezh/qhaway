"""
GET /api/bias/troudet — métricas de sesgo taxonómico (Troudet et al. 2017)

Calcula por clase:
  - n_species: especies en la clase
  - n_obs: observaciones totales
  - ideal: muestreo ideal = total_obs × (n_species_clase / n_species_total)
  - deviation: n_obs - ideal (positivo = sobremuestreado)
  - p1: % especies con ≥1 observación
  - p20: % especies con ≥20 observaciones
  - p20d: % especies con ≥20 celdas H3 distintas (cobertura espacial)
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import json

from backend.dashboard.cache import AGG, ECO_H3
from backend.dashboard.filters import apply_taxa, apply_ecoregions

router = APIRouter()


@router.get("/troudet")
def troudet(
    kingdom: str = Query(""),
    phylum:  str = Query(""),
    klass:   str = Query("", alias="class"),
    order:   str = Query(""),
    eco_ids: str = Query(""),
    grade:   str = Query("all"),
):
    df = AGG["species_list"].copy()
    df = apply_taxa(df, kingdom, phylum, klass, order)
    df = apply_ecoregions(df, eco_ids, ECO_H3)
    if grade != "all":
        df = df[df["quality_grade"] == grade]

    if df.empty:
        return JSONResponse({"data": [], "totals": {}})

    total_obs = int(df["n_obs"].sum())
    total_species = len(df)

    # Agrupar por clase
    rows = []
    for cls, grp in df.groupby("class", dropna=True):
        if not cls or cls == "":
            continue
        n_sp = len(grp)
        n_obs = int(grp["n_obs"].sum())
        ideal = total_obs * (n_sp / total_species) if total_species > 0 else 0
        deviation = n_obs - ideal

        p1 = (grp["n_obs"] >= 1).sum() / n_sp * 100 if n_sp > 0 else 0
        p20 = (grp["n_obs"] >= 20).sum() / n_sp * 100 if n_sp > 0 else 0
        p20d = (grp["n_cells"] >= 20).sum() / n_sp * 100 if n_sp > 0 else 0

        rows.append({
            "class": cls,
            "kingdom": grp["kingdom"].iloc[0] if "kingdom" in grp.columns else None,
            "n_species": n_sp,
            "n_obs": n_obs,
            "ideal": round(ideal, 1),
            "deviation": round(deviation, 1),
            "deviation_pct": round(deviation / ideal * 100, 1) if ideal > 0 else 0,
            "p1": round(p1, 1),
            "p20": round(p20, 1),
            "p20d": round(p20d, 1),
        })

    rows.sort(key=lambda r: r["deviation"], reverse=True)

    return JSONResponse({
        "total_obs": total_obs,
        "total_species": total_species,
        "n_classes": len(rows),
        "data": rows,
    })
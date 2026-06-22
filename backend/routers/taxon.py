"""
GET /api/taxon/tree     — bar chart taxonómico
GET /api/taxon/options  — opciones disponibles para el filtro cascada
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import pandas as pd

from backend.dashboard.cache import AGG, ECO_H3, ECO_META
from backend.dashboard.filters import apply_taxa, apply_ecoregions

router = APIRouter()

LEVELS = ["kingdom", "phylum", "class", "order", "family", "genus"]


@router.get("/tree")
def taxon_tree(
    kingdom: str = Query(""),
    phylum:  str = Query(""),
    klass:   str = Query("", alias="class"),
    order:   str = Query(""),
    eco_ids: str = Query(""),
    depth:   int = Query(4, ge=2, le=6),
    grade:   str = Query("all"),
):
    df: pd.DataFrame = AGG["taxon_tree"].copy()
    df = apply_taxa(df, kingdom, phylum, klass, order)
    df = apply_ecoregions(df, eco_ids, ECO_H3)
    if grade != "all":
        df = df[df["quality_grade"] == grade]

    group_cols = LEVELS[:depth]

    agg = (
        df.groupby(group_cols, dropna=True)
        .agg(n_species=("n_species", "sum"), n_obs=("n_obs", "sum"))
        .reset_index()
    )

    agg["path"] = agg[group_cols].apply(
        lambda r: "/".join(str(v) for v in r if pd.notna(v) and v != ""),
        axis=1,
    )

    records = agg[["path", "n_species", "n_obs"]].to_dict(orient="records")

    return JSONResponse({
        "depth":   depth,
        "n_nodes": len(records),
        "data":    records,
    })


@router.get("/options")
def taxon_options(
    kingdom: str = Query(""),
    phylum:  str = Query(""),
    klass:   str = Query("", alias="class"),
    grade:   str = Query("all"),
):
    """
    Devuelve las opciones disponibles en cada nivel taxonómico,
    filtradas por las selecciones de los niveles superiores.
    Cada nivel: [{value, n_species}] ordenado por n_species desc.
    """
    df: pd.DataFrame = AGG["taxon_tree"].copy()
    if grade != "all":
        df = df[df["quality_grade"] == grade]

    def opts(frame, col):
        g = (
            frame.groupby(col, dropna=True)
            .agg(n_species=("n_species", "sum"))
            .reset_index()
            .sort_values("n_species", ascending=False)
        )
        return [
            {"value": row[col], "n": int(row["n_species"])}
            for _, row in g.iterrows()
            if pd.notna(row[col]) and row[col] != ""
        ]

    # Cada nivel se filtra por las selecciones de los niveles superiores
    kingdoms = opts(df, "kingdom")

    df_k = df[df["kingdom"].isin(kingdom.split(","))] if kingdom else df
    phyla = opts(df_k, "phylum")

    df_p = df_k[df_k["phylum"].isin(phylum.split(","))] if phylum else df_k
    classes = opts(df_p, "class")

    df_c = df_p[df_p["class"].isin(klass.split(","))] if klass else df_p
    orders = opts(df_c, "order")

    return JSONResponse({
        "kingdom": kingdoms,
        "phylum":  phyla,
        "class":   classes,
        "order":   orders,
    })


@router.get("/ecoregions")
def ecoregions_meta():
    """Metadata de ecorregiones para el sidebar (bioma → ecorregión)."""
    return JSONResponse(ECO_META)
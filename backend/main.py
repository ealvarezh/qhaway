from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.dashboard.cache import init, cache_stats
from backend.routers import map, species, temporal, taxon, stats, bias, external_species

_ROOT = Path(__file__).parent.parent
_BOUNDARIES = _ROOT / 'data' / 'processed' / 'boundaries'


@asynccontextmanager
async def lifespan(app: FastAPI):
    init()
    yield


app = FastAPI(title="Biodiversity Explorer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(map.router,      prefix="/api/map")
app.include_router(species.router,  prefix="/api/species")
app.include_router(temporal.router, prefix="/api/temporal")
app.include_router(taxon.router,    prefix="/api/taxon")
app.include_router(stats.router,    prefix="/api/stats")
app.include_router(bias.router,     prefix="/api/bias")
app.include_router(external_species.router, prefix="/api/external_species")


@app.get("/api/status")
def status():
    return cache_stats()


@app.get("/api/ecoregions/geojson")
def ecoregions_geojson():
    path = _BOUNDARIES / 'ecoregions.geojson'
    return FileResponse(path, media_type="application/geo+json")
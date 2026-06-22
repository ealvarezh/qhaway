"""Pipeline VR-RAG (Visual Retrieval RAG) para identificación de insectos/artrópodos.

Replica la lógica de C:\\estela\\tf\\big_data_project\\src\\test_vr_rag_insecta.py:

  Etapa 1 — Recuperación cross-modal: la imagen subida se compara contra los
            embeddings de TEXTO (descripciones taxonómicas) precalculados con
            BioCLIP + CLIP (ensemble). Da un top-m de candidatos por similitud
            imagen-texto.
  Etapa 2 — Re-ranking visual: la imagen subida se compara contra los
            embeddings de IMÁGENES ancla (DINOv2) de cada candidato de la
            etapa 1. score_final = lam*score_ensemble + (1-lam)*score_dino.
  Etapa 3 — Deliberación final: se decide la especie ganadora según el
            score_final del top-1 y el margen frente al top-2.

Los embeddings "gold" (texto y DINO) ya están precomputados y copiados desde
tf en data/processed/external_tf/parquets/.../data/gold/. Solo la imagen
subida por el usuario se codifica en caliente.
"""
from __future__ import annotations

import glob
import threading
from pathlib import Path

import pandas as pd
import torch
from PIL import Image

_DATA_ROOT = Path('data/processed/external_tf')
_GOLD_ROOT = _DATA_ROOT / 'parquets/big_data_project/data/gold'
_SPECIES_LIST = _DATA_ROOT / 'species_list.parquet'

_LOCK = threading.Lock()
_STATE = {}


def _read_parquet_dir(path: Path) -> pd.DataFrame:
    files = sorted(glob.glob(str(path / '*.parquet')))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def _load_species_meta() -> pd.DataFrame:
    if not _SPECIES_LIST.exists():
        return pd.DataFrame(columns=['slug', 'name', 'family', 'order', 'image_url', 'dataset_records', 'subrepresented'])
    df = pd.read_parquet(_SPECIES_LIST)
    df = df[df['name'].notna()].copy()
    df['slug'] = df['name'].astype(str).str.lower().str.replace(' ', '_', regex=False)
    df = df.drop_duplicates(subset='slug', keep='first')
    return df


def _load_state():
    """Carga (una sola vez) modelos y embeddings gold. Lazy + thread-safe."""
    with _LOCK:
        if _STATE.get('ready'):
            return _STATE

        import open_clip
        from transformers import AutoImageProcessor, AutoModel

        device = 'cuda' if torch.cuda.is_available() else 'cpu'

        bio_model, _, bio_pre = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip')
        bio_model = bio_model.to(device).eval()

        clip_model, _, clip_pre = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')
        clip_model = clip_model.to(device).eval()

        dino_proc = AutoImageProcessor.from_pretrained('facebook/dinov2-small')
        dino_model = AutoModel.from_pretrained('facebook/dinov2-small').to(device).eval()

        text_clip = _read_parquet_dir(_GOLD_ROOT / 'embeddings_textuales_distribuidos/clip')
        text_bioclip = _read_parquet_dir(_GOLD_ROOT / 'embeddings_textuales_distribuidos/bioclip')
        dino_df = _read_parquet_dir(_GOLD_ROOT / 'embeddings_imagenes_distribuidas/dino')

        species_meta = _load_species_meta().set_index('slug')

        # Alinear texto: usamos id_str de CLIP como referencia y buscamos su par en BioCLIP.
        bioclip_by_id = {row['id_str']: row['embedding'] for _, row in text_bioclip.iterrows()}
        ids, clip_embs, bio_embs, descriptions = [], [], [], []
        for _, row in text_clip.iterrows():
            sid = row['id_str']
            if sid not in bioclip_by_id:
                continue
            ids.append(sid)
            clip_embs.append(row['embedding'])
            bio_embs.append(bioclip_by_id[sid])
            descriptions.append(row.get('description', ''))

        text_clip_t = torch.tensor(clip_embs, dtype=torch.float32, device=device)
        text_bio_t = torch.tensor(bio_embs, dtype=torch.float32, device=device)

        dino_by_species: dict[str, torch.Tensor] = {}
        for sid, group in dino_df.groupby('id_str'):
            dino_by_species[sid] = torch.tensor(list(group['embedding']), dtype=torch.float32, device=device)

        _STATE.update({
            'ready': True,
            'device': device,
            'clip_model': clip_model,
            'clip_pre': clip_pre,
            'bio_model': bio_model,
            'bio_pre': bio_pre,
            'dino_model': dino_model,
            'dino_proc': dino_proc,
            'ids': ids,
            'descriptions': descriptions,
            'text_clip': text_clip_t,
            'text_bio': text_bio_t,
            'dino_by_species': dino_by_species,
            'species_meta': species_meta,
        })
        return _STATE


def _species_info(slug: str, description: str, species_meta: pd.DataFrame) -> dict:
    if slug in species_meta.index:
        row = species_meta.loc[slug]
        return {
            'name': row['name'],
            'family': row.get('family'),
            'order': row.get('order'),
            'image_url': row.get('image_url'),
            'dataset_records': row.get('dataset_records'),
            'subrepresented': bool(row.get('subrepresented')) if pd.notna(row.get('subrepresented')) else False,
            'description': description,
        }
    pretty = slug.replace('_', ' ').capitalize()
    return {'name': pretty, 'family': None, 'order': None, 'image_url': None,
            'dataset_records': None, 'subrepresented': False, 'description': description}


@torch.no_grad()
def _encode_clip(model, preprocess, img: Image.Image, device: str) -> torch.Tensor:
    t = preprocess(img).unsqueeze(0).to(device)
    e = model.encode_image(t)
    return e / e.norm(dim=-1, keepdim=True)


@torch.no_grad()
def _encode_dino(model, proc, img: Image.Image, device: str) -> torch.Tensor:
    inputs = proc(images=img, return_tensors='pt').to(device)
    out = model(**inputs)
    e = out.last_hidden_state[:, 0, :]
    return e / e.norm(dim=-1, keepdim=True)


def stage1_retrieval(img: Image.Image, top_m: int = 30) -> list[dict]:
    """Etapa 1 — ranking imagen vs embeddings de texto (BioCLIP + CLIP ensemble)."""
    st = _load_state()
    device = st['device']

    q_clip = _encode_clip(st['clip_model'], st['clip_pre'], img, device)
    q_bio = _encode_clip(st['bio_model'], st['bio_pre'], img, device)

    score_clip = (q_clip @ st['text_clip'].T).squeeze(0)
    score_bio = (q_bio @ st['text_bio'].T).squeeze(0)
    ensemble = (score_clip + score_bio) / 2.0

    top_idx = ensemble.argsort(descending=True)[:top_m]
    results = []
    for rank, idx in enumerate(top_idx.tolist()):
        slug = st['ids'][idx]
        info = _species_info(slug, st['descriptions'][idx], st['species_meta'])
        results.append({
            'rank': rank + 1,
            'slug': slug,
            **info,
            'score_bioclip': round(score_bio[idx].item(), 4),
            'score_clip': round(score_clip[idx].item(), 4),
            'score_ensemble': round(ensemble[idx].item(), 4),
        })
    return results


def stage2_reranking(img: Image.Image, candidates: list[dict], lam: float = 0.7, top_k: int = 10) -> list[dict]:
    """Etapa 2 — re-ranking imagen vs imágenes ancla (DINOv2) de cada candidato."""
    st = _load_state()
    device = st['device']
    q_dino = _encode_dino(st['dino_model'], st['dino_proc'], img, device)

    reranked = []
    for cand in candidates:
        anchors = st['dino_by_species'].get(cand['slug'])
        s_dino = 0.0
        if anchors is not None and anchors.numel() > 0:
            sims = (q_dino @ anchors.T).squeeze(0)
            s_dino = sims.max().item()
        s_final = lam * cand['score_ensemble'] + (1 - lam) * s_dino
        reranked.append({**cand, 'score_dino': round(s_dino, 4), 'score_final': round(s_final, 4)})

    reranked.sort(key=lambda x: x['score_final'], reverse=True)
    for i, r in enumerate(reranked):
        r['rank_final'] = i + 1
        r['rank_delta'] = r['rank'] - r['rank_final']
    return reranked[:top_k]


def stage3_deliberation(top_k: list[dict]) -> dict:
    """Etapa 3 — deliberación final sobre el top-k re-rankeado.

    Sin el LLM (DeepSeek) usado en tf, que requiere una API key externa:
    la decisión se basa en el score_final del top-1, el margen frente al
    top-2 y el consenso taxonómico (familia/orden) dentro del top-k —
    misma señal que tf usa para fijar la confianza antes de narrarla.
    """
    if not top_k:
        return {'predicted_species': None, 'confidence': 'baja', 'rationale': 'Sin candidatos.'}

    top1 = top_k[0]
    top2 = top_k[1] if len(top_k) > 1 else None
    margin = (top1['score_final'] - top2['score_final']) if top2 else top1['score_final']

    family_votes = sum(1 for r in top_k if r.get('family') and r['family'] == top1.get('family'))
    order_votes = sum(1 for r in top_k if r.get('order') and r['order'] == top1.get('order'))
    family_consensus = family_votes / len(top_k)
    order_consensus = order_votes / len(top_k)

    if top1['score_final'] > 0.85 and margin > 0.03:
        confidence = 'alta'
    elif top1['score_final'] > 0.70:
        confidence = 'media'
    else:
        confidence = 'baja'

    rationale_parts = [
        f"Top-1 '{top1['name']}' con score_final={top1['score_final']:.4f}",
        f"margen sobre #2 = {margin:.4f}",
        f"consenso de familia en top-{len(top_k)} = {family_consensus*100:.0f}%",
        f"consenso de orden = {order_consensus*100:.0f}%",
    ]
    if top1.get('subrepresented'):
        rationale_parts.append('especie subrepresentada en el dataset (pocos registros de referencia)')

    return {
        'predicted_species': top1['name'],
        'family': top1.get('family'),
        'order': top1.get('order'),
        'confidence': confidence,
        'margin': round(margin, 4),
        'family_consensus': round(family_consensus, 2),
        'order_consensus': round(order_consensus, 2),
        'rationale': '; '.join(rationale_parts) + '.',
    }


def run_pipeline(img: Image.Image, top_m: int = 30, top_k: int = 10, lam: float = 0.7) -> dict:
    stage1 = stage1_retrieval(img, top_m=top_m)
    stage2 = stage2_reranking(img, stage1, lam=lam, top_k=top_k)
    stage3 = stage3_deliberation(stage2)
    return {'stage1': stage1, 'stage2': stage2, 'stage3': stage3}

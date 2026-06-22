import { useState, useMemo } from 'react'

export default function SearchBichos() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [known, setKnown] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const commonMatch = useMemo(() => {
    if (!results) return null
    if (results.source === 'vr_rag') return 'VR-RAG (texto + re-ranking visual)'
    if (results.source === 'text_match') return 'Texto similar'
    if (results.source === 'batch_results') return 'Resultado de batch'
    if (results.source === 'local_match') return 'Imagen conocida localmente'
    return results.source
  }, [results])

  const topTax = useMemo(() => {
    const top = results?.predictions?.[0]
    return {
      family: top?.family || null,
      order: top?.order || null,
    }
  }, [results])

  async function submit(e) {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    setError(null)
    setResults(null)

    const fd = new FormData()
    fd.append('file', file)
    if (known) fd.append('known_species', known)

    try {
      const res = await fetch('/api/external_species/predict', { method: 'POST', body: fd })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const j = await res.json()
      setResults(j)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleFileChange(e) {
    const selected = e.target.files?.[0] || null
    setFile(selected)
    setResults(null)
    setError(null)
    if (selected) {
      const url = URL.createObjectURL(selected)
      setPreview(url)
    } else {
      setPreview(null)
    }
  }

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div>
          <h2 style={s.title}>Búsqueda Bichos</h2>
          <p style={s.subtitle}>Sube una foto y revisa las mejores coincidencias con el dataset externo.</p>
        </div>
      </div>

      <form onSubmit={submit} style={s.form}>
        <label style={s.field}>
          <span style={s.label}>Imagen</span>
          <input type="file" accept="image/*" onChange={handleFileChange} />
        </label>

        <label style={s.field}>
          <span style={s.label}>Especie conocida (opcional)</span>
          <input
            style={s.input}
            placeholder="Ej. Stenaspis superba"
            value={known}
            onChange={e => setKnown(e.target.value)}
          />
        </label>

        <button type="submit" style={s.button} disabled={loading || !file}>
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </form>

      {error && <div style={s.error}>{error}</div>}

      {preview && (
        <div style={s.previewRow}>
          <div style={s.previewCard}>
            <div style={s.previewLabel}>Imagen subida</div>
            <img src={preview} alt="preview" style={s.previewImage} />
            <div style={s.previewName}>{file?.name}</div>
          </div>
        </div>
      )}

      {results && (
        <section style={s.resultsSection}>
          <div style={s.resultsHeader}>
            <div>
              <div style={s.resultSource}>Resultado: {commonMatch}</div>
              {results.known_species && (
                <div style={s.resultMeta}>
                  Conocida: <strong>{results.known_species}</strong> · Top1 acertado: {results.top1_is_known ? 'sí' : 'no'}
                </div>
              )}
              {results.matched_species && (
                <div style={s.resultMeta}>Especie local detectada: <strong>{results.matched_species}</strong></div>
              )}
            </div>
          </div>

          {results.stage1 && (
            <div style={s.stageBlock}>
              <div style={s.stageTitle}>Etapa 1 — Ranking imagen vs. texto (BioCLIP + CLIP)</div>
              <div style={s.stageList}>
                {results.stage1.map((c, i) => (
                  <div key={i} style={s.stageRow}>
                    <span style={s.stageRank}>#{c.rank}</span>
                    <span style={s.stageName}>{c.name}</span>
                    <span style={s.stageScore}>ensemble {c.score_ensemble?.toFixed(3)}</span>
                    <span style={s.stageScoreMuted}>bioclip {c.score_bioclip?.toFixed(3)} · clip {c.score_clip?.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {results.stage3 && (
            <div style={s.stageBlock}>
              <div style={s.stageTitle}>Etapa 3 — Deliberación final</div>
              <div style={s.deliberation}>
                <div style={s.deliberationHeadline}>
                  <strong>{results.stage3.predicted_species}</strong>
                  <span style={s.confidenceBadge(results.stage3.confidence)}>confianza {results.stage3.confidence}</span>
                </div>
                <div style={s.resultMeta}>{results.stage3.rationale}</div>
              </div>
            </div>
          )}

          {results.stage2 && <div style={s.stageTitle}>Etapa 2 — Re-ranking visual (DINOv2)</div>}
          <div style={s.cardGrid}>
            {results.predictions?.map((item, index) => {
              const isTop = index === 0
              const familyMatch = topTax.family && item.family && topTax.family === item.family
              const orderMatch = topTax.order && item.order && topTax.order === item.order
              const cardStyle = isTop ? (results.top1_is_known ? { ...s.card, ...s.cardTopOk } : { ...s.card, ...s.cardTopBad }) : s.card
              return (
              <div key={index} style={cardStyle}>
                <div style={s.cardImageWrap}>
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.name} style={s.cardImage} />
                  ) : (
                    <div style={s.cardImageEmpty}>sin imagen</div>
                  )}
                </div>

                <div style={s.cardBody}>
                  <div style={s.cardRank}>#{index + 1}</div>
                  <div style={s.cardName}>{item.name}</div>
                  {isTop && results.top1_is_known !== undefined && (
                    <div style={s.topBadge}>{results.top1_is_known ? 'Top1: acertado' : 'Top1: no'}</div>
                  )}
                  {item.family && <div style={s.cardTaxon}>Familia: {item.family}</div>}
                  {item.order && <div style={s.cardTaxon}>Orden: {item.order}</div>}
                  <div style={s.cardScore}>
                    Similitud: {(((item.score_final ?? item.score) ?? 0) * 100).toFixed(1)}%
                  </div>
                  {item.score_dino != null && (
                    <div style={s.cardSmall}>cross {item.score_ensemble?.toFixed(3)} · dino {item.score_dino?.toFixed(3)}</div>
                  )}
                  {item.dataset_records != null && (
                    <div style={s.cardSmall}>Registros: {item.dataset_records}</div>
                  )}
                  {!isTop && (familyMatch || orderMatch) && (
                    <div style={s.matchHint}>
                      {familyMatch && <span>Coincide en familia</span>}
                      {familyMatch && orderMatch && <span> · </span>}
                      {orderMatch && <span>Coincide en orden</span>}
                    </div>
                  )}
                </div>
              </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}

const s = {
  page: { padding: '28px 40px', display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 1100, margin: '0 auto' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 20 },
  title: { margin: 0, fontSize: 28, letterSpacing: '0.02em' },
  subtitle: { margin: '8px 0 0', color: 'var(--text-3)', maxWidth: 720 },
  form: { display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end' },
  field: { display: 'flex', flexDirection: 'column', gap: 6, minWidth: 220 },
  label: { fontSize: 12, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em' },
  input: { padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 8, background: 'var(--surface-2)', color: 'var(--text)', minWidth: 260 },
  button: { padding: '12px 18px', border: 'none', borderRadius: 10, background: 'var(--accent)', color: '#fff', cursor: 'pointer', minWidth: 140, fontWeight: 700 },
  error: { padding: 14, borderRadius: 12, background: 'rgba(191, 28, 28, 0.12)', color: '#bf1c1c' },
  previewRow: { display: 'flex', gap: 16, flexWrap: 'wrap' },
  previewCard: { width: 360, borderRadius: 16, overflow: 'hidden', border: '1px solid var(--border)', background: 'var(--surface-2)', boxShadow: '0 12px 30px rgba(0,0,0,0.05)' },
  previewLabel: { padding: '12px 16px', fontSize: 12, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em' },
  previewImage: { width: '100%', display: 'block', objectFit: 'cover', aspectRatio: '4 / 3' },
  previewName: { padding: '12px 16px', fontSize: 15, color: 'var(--text)' },
  resultsSection: { display: 'flex', flexDirection: 'column', gap: 12, padding: '0 12px', maxHeight: '56vh', overflowY: 'auto', paddingBottom: 12 },
  resultsHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 },
  resultSource: { fontSize: 13, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.08em' },
  resultMeta: { marginTop: 6, fontSize: 13, color: 'var(--text-3)' },
  cardGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14, padding: '0 40px' },
  card: { borderRadius: 18, overflow: 'hidden', border: '1px solid var(--border)', background: 'var(--surface-2)', display: 'flex', flexDirection: 'column', minHeight: 320 },
  cardImageWrap: { minHeight: 170, background: 'var(--surface)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  cardImage: { width: '100%', height: '100%', objectFit: 'cover' },
  cardImageEmpty: { width: '100%', padding: 20, textAlign: 'center', color: 'var(--text-3)' },
  cardBody: { padding: 12, display: 'grid', gap: 6, flex: 1 },
  cardRank: { fontSize: 12, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em' },
  cardName: { fontSize: 18, fontWeight: 700, lineHeight: 1.25 },
  cardTaxon: { fontSize: 14, color: 'var(--text-3)' },
  cardScore: { marginTop: 6, fontSize: 15, fontWeight: 700, color: 'var(--accent-glow)' },
  cardSmall: { fontSize: 13, color: 'var(--text-3)' },
  cardTopOk: { borderColor: 'rgba(74, 222, 128, 0.9)', boxShadow: '0 8px 24px rgba(74, 222, 128, 0.06)' },
  cardTopBad: { borderColor: 'rgba(239, 68, 68, 0.9)', boxShadow: '0 8px 24px rgba(239, 68, 68, 0.06)' },
  topBadge: { marginTop: 6, padding: '6px 8px', borderRadius: 8, background: 'rgba(0,0,0,0.12)', color: 'var(--text-2)', fontSize: 12, display: 'inline-block' },
  matchHint: { marginTop: 8, fontSize: 13, color: 'var(--text-2)' },
  stageBlock: { padding: '0 12px', display: 'flex', flexDirection: 'column', gap: 8 },
  stageTitle: { fontSize: 13, fontWeight: 700, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '0 12px' },
  stageList: { display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 160, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 10, padding: 8, background: 'var(--surface-2)' },
  stageRow: { display: 'flex', gap: 10, alignItems: 'baseline', fontSize: 13 },
  stageRank: { color: 'var(--text-3)', minWidth: 28 },
  stageName: { fontWeight: 600, flex: 1 },
  stageScore: { color: 'var(--accent-glow)', fontWeight: 700 },
  stageScoreMuted: { color: 'var(--text-3)', fontSize: 12 },
  deliberation: { border: '1px solid var(--border)', borderRadius: 10, padding: 12, background: 'var(--surface-2)', display: 'flex', flexDirection: 'column', gap: 6 },
  deliberationHeadline: { display: 'flex', alignItems: 'center', gap: 10, fontSize: 16 },
  confidenceBadge: (level) => ({
    padding: '4px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700, textTransform: 'uppercase',
    background: level === 'alta' ? 'rgba(74, 222, 128, 0.18)' : level === 'media' ? 'rgba(250, 204, 21, 0.18)' : 'rgba(239, 68, 68, 0.18)',
    color: level === 'alta' ? '#15803d' : level === 'media' ? '#a16207' : '#b91c1c',
  }),
}

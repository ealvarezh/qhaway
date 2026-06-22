import { useFilters, taxaParams } from '../hooks/useFilters'
import { useApi }     from '../hooks/useApi'
import { api }        from '../lib/api'
import TaxonFilter    from './TaxonFilter'
import GeoFilter      from './GeoFilter'

const NAV = [
  { key: 'ecoregions', label: 'Ecorregiones',  icon: IconGlobe },
  { key: 'sightings',  label: 'Avistamientos', icon: IconHex },
  { key: 'taxon',      label: 'Taxonomía',     icon: IconTree },
  { key: 'cobertura',  label: 'Cobertura',     icon: IconGrid },
  { key: 'temporal',   label: 'Temporal',      icon: IconChart },
  { key: 'species',    label: 'Especies',      icon: IconCards },
  { key: 'search',     label: 'Búsqueda Bichos', icon: IconSearch },
]

export default function Shell({ activeView, viewLabel, onNav, children }) {
  const { filters, set, reset, toggleResearchMode } = useFilters()
  const { data: stats } = useApi(api.stats, taxaParams(filters))

  const researchActive = filters.kingdom.includes('Animalia') &&
                         filters.phylum.includes('Arthropoda') &&
                         filters.eco_ids.length > 0

  return (
    <div style={s.shell}>
      {/* SIDEBAR */}
      <aside style={s.sidebar}>
        {/* Fixed header */}
        <div style={s.sideHeader}>
          <div style={s.globeWrap}><SidebarGlobe /></div>
          <div style={s.logo}>
            <div style={s.logoName}>Qhaway</div>
            <div style={s.logoSub}>iNaturalist · GBIF</div>
          </div>
        </div>

        {/* Scrollable middle */}
        <div style={s.sideScroll}>
          <nav style={s.nav}>
            {NAV.map(({ key, label, icon: Icon }) => (
              <div
                key={key}
                style={{ ...s.navItem, ...(activeView === key ? s.navActive : {}) }}
                onClick={() => onNav(key)}
              >
                <Icon size={15} />
                <span style={s.navLabel}>{label}</span>
              </div>
            ))}
          </nav>

          {/* Taxonomic filter */}
          <div style={s.sideSection}>
            <div style={s.sideLabel}>Taxonomía</div>
            <TaxonFilter />
          </div>

          {/* Geographic filter */}
          <div style={s.sideSection}>
            <div style={s.sideLabel}>Geografía</div>
            <GeoFilter />
          </div>

          {/* Year range */}
          <div style={s.sideSection}>
            <div style={s.sideLabel}>Año</div>
            <div style={s.yearRow}>
              <input
                type="number" style={s.yearInput}
                value={filters.year_min}
                onChange={e => set('year_min', +e.target.value)}
                min={1950} max={filters.year_max}
              />
              <span style={{ color: 'var(--text-3)', fontSize: 11 }}>–</span>
              <input
                type="number" style={s.yearInput}
                value={filters.year_max}
                onChange={e => set('year_max', +e.target.value)}
                min={filters.year_min} max={2025}
              />
            </div>
          </div>
        </div>

        {/* Fixed footer */}
        <div style={s.footer}>
          <div style={s.footerRow}><span>Observaciones</span><span style={s.footerVal}>{stats ? (stats.n_obs / 1e6).toFixed(1) + 'M' : '–'}</span></div>
          <div style={s.footerRow}><span>Especies</span>    <span style={s.footerVal}>{stats ? stats.n_species.toLocaleString() : '–'}</span></div>
          <div style={s.footerRow}><span>Celdas H3</span>   <span style={s.footerVal}>{stats ? stats.n_cells.toLocaleString() : '–'}</span></div>
          <div
            style={{ ...s.footerRow, marginTop: 8, cursor: 'pointer', color: 'var(--text-3)' }}
            onClick={reset}
          >
            reset filtros
          </div>
        </div>
      </aside>

      {/* MAIN */}
      <div style={s.main}>
        <div style={s.topbar}>
          <span style={s.viewTitle}>{viewLabel}</span>
          <div style={s.topbarSpacer} />
          <Chip
            active={filters.grade === 'research'}
            onClick={() => set('grade', 'research')}
          >
            research grade
          </Chip>
          <Chip
            active={filters.grade === 'all'}
            onClick={() => set('grade', 'all')}
          >
            all grades
          </Chip>
          <div style={s.topbarDivider} />
          <Chip
            active={researchActive}
            onClick={toggleResearchMode}
          >
            investigation
          </Chip>
        </div>
        <div style={s.content}>
          {children}
        </div>
      </div>
    </div>
  )
}

function Chip({ children, active, onClick }) {
  return (
    <div onClick={onClick} style={{ ...s.chip, ...(active ? s.chipActive : {}) }}>
      {active && <div style={s.chipDot} />}
      {children}
    </div>
  )
}

// ── Inline styles ──────────────────────────────────────────────────────────
const s = {
  shell:   { display:'flex', height:'100vh' },
  sidebar: { width:220, flexShrink:0, background:'var(--surface)', borderRight:'1px solid var(--border)', display:'flex', flexDirection:'column', overflow:'hidden' },
  sideHeader: { flexShrink:0, borderBottom:'1px solid var(--border)' },
  sideScroll: { flex:1, overflowY:'auto', overflowX:'hidden' },
  main:    { flex:1, display:'flex', flexDirection:'column', overflow:'hidden', minWidth:0 },

  logo:    { padding:'10px 20px 14px' },
  globeWrap:{ padding:'12px 0 0', display:'flex', justifyContent:'center' },
  logoName:{ fontFamily:'var(--font-display)', fontSize:18, fontWeight:700, letterSpacing:'0.08em', color:'var(--accent-glow)', textTransform:'uppercase' },
  logoSub: { fontSize:10, color:'var(--text-3)', letterSpacing:'0.12em', marginTop:2 },

  nav:     { padding:'12px 0' },
  navItem: { display:'flex', alignItems:'center', gap:12, padding:'10px 20px', cursor:'pointer', borderLeft:'2px solid transparent', color:'var(--text-2)', fontFamily:'var(--font-display)', fontSize:13, fontWeight:600, letterSpacing:'0.06em', textTransform:'uppercase', transition:'background 0.15s' },
  navActive:{ background:'var(--surface-3)', borderLeftColor:'var(--accent)', color:'var(--accent-glow)' },
  navLabel:{ fontFamily:'var(--font-display)', fontSize:13, fontWeight:600, letterSpacing:'0.06em', textTransform:'uppercase' },

  sideSection:{ padding:'12px 20px', borderTop:'1px solid var(--border)' },
  sideLabel:  { fontSize:10, color:'var(--text-3)', letterSpacing:'0.1em', textTransform:'uppercase', marginBottom:8 },
  kingdomItem:{ fontSize:12, color:'var(--text-2)', padding:'4px 0', cursor:'pointer' },
  kingdomActive:{ color:'var(--accent-glow)' },
  yearRow:    { display:'flex', alignItems:'center', gap:8 },
  yearInput:  { background:'var(--surface-2)', border:'1px solid var(--border-2)', color:'var(--text)', fontFamily:'var(--font-mono)', fontSize:12, padding:'4px 8px', width:70, outline:'none' },

  footer:    { flexShrink:0, padding:'14px 20px', borderTop:'1px solid var(--border)', fontSize:11, color:'var(--text-3)' },
  footerRow: { display:'flex', justifyContent:'space-between', lineHeight:1.8 },
  footerVal: { color:'var(--text-2)', fontWeight:500 },

  topbar:      { height:50, background:'var(--surface)', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', padding:'0 20px', gap:10, flexShrink:0 },
  viewTitle:   { fontFamily:'var(--font-display)', fontSize:14, fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', color:'var(--text-2)' },
  topbarSpacer:{ flex:1 },
  topbarDivider:{ width:1, height:20, background:'var(--border-2)' },
  chip:        { display:'inline-flex', alignItems:'center', gap:6, padding:'4px 10px', border:'1px solid var(--border-2)', borderColor:'var(--border-2)', fontSize:11, color:'var(--text-2)', cursor:'pointer', background:'transparent' },
  chipActive:  { borderColor:'var(--accent)', color:'var(--accent-glow)', background:'rgba(78,144,104,0.08)' },
  chipDot:     { width:6, height:6, borderRadius:'50%', background:'currentColor' },

  content: { flex:1, overflow:'hidden', position:'relative' },
}

// ── SVG icons ──────────────────────────────────────────────────────────────
function SidebarGlobe() {
  return (
    <svg width="180" height="130" viewBox="20 20 120 120" style={{ display:'block', margin:'0 auto' }}>
      <style>{`
        @keyframes globe-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes globe-pulse { 0%,100% { opacity:0.4; } 50% { opacity:0.8; } }
        .g-mer { animation: globe-spin 12s linear infinite; transform-origin: 80px 80px; }
        .g-dot { animation: globe-pulse 3s ease-in-out infinite; }
      `}</style>
      <circle cx="80" cy="80" r="52" fill="none" stroke="#1e2e1f" strokeWidth="0.5"/>
      <circle cx="80" cy="80" r="52" fill="none" stroke="#2d5c3f" strokeWidth="0.8"/>
      <circle cx="80" cy="80" r="38" fill="none" stroke="#1e2e1f" strokeWidth="0.5"/>
      <circle cx="80" cy="80" r="22" fill="none" stroke="#1e2e1f" strokeWidth="0.5"/>
      <line x1="28" y1="80" x2="132" y2="80" stroke="#1e2e1f" strokeWidth="0.5"/>
      <g className="g-mer">
        <ellipse cx="80" cy="80" rx="18" ry="52" fill="none" stroke="#4e9068" strokeWidth="0.7" opacity="0.6"/>
        <ellipse cx="80" cy="80" rx="36" ry="52" fill="none" stroke="#4e9068" strokeWidth="0.7" opacity="0.4"/>
        <ellipse cx="80" cy="80" rx="50" ry="52" fill="none" stroke="#4e9068" strokeWidth="0.7" opacity="0.25"/>
      </g>
      <ellipse cx="80" cy="80" rx="52" ry="14" fill="none" stroke="#2d5c3f" strokeWidth="0.5" transform="rotate(-23 80 80)"/>
      <ellipse cx="80" cy="80" rx="52" ry="14" fill="none" stroke="#2d5c3f" strokeWidth="0.5" transform="rotate(23 80 80)"/>
      <circle className="g-dot" cx="62" cy="58" r="2" fill="#6db88a"/>
      <circle className="g-dot" cx="95" cy="72" r="1.5" fill="#6db88a" style={{ animationDelay:'0.5s' }}/>
      <circle className="g-dot" cx="78" cy="95" r="1.8" fill="#6db88a" style={{ animationDelay:'1s' }}/>
      <circle className="g-dot" cx="88" cy="55" r="1.2" fill="#4e9068" style={{ animationDelay:'1.5s' }}/>
      <circle className="g-dot" cx="70" cy="80" r="1.4" fill="#4e9068" style={{ animationDelay:'2s' }}/>
      <circle cx="80" cy="80" r="3" fill="#6db88a" opacity="0.6"/>
      <circle cx="80" cy="80" r="1.5" fill="#c4ffda"/>
    </svg>
  )
}

function IconGlobe({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="8" cy="8" r="6.5"/>
    <path d="M1.5 8h13M8 1.5C6 4 5 6 5 8s1 4 3 6.5M8 1.5C10 4 11 6 11 8s-1 4-3 6.5"/>
  </svg>
}
function IconHex({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M8 1L14 4.5V11.5L8 15L2 11.5V4.5L8 1Z"/>
  </svg>
}
function IconTree({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="8" cy="3" r="1.5"/><circle cx="3" cy="11" r="1.5"/><circle cx="13" cy="11" r="1.5"/>
    <path d="M8 4.5v3L3 9.5M8 7.5l5 2"/>
  </svg>
}
function IconGrid({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/>
    <rect x="2" y="9" width="5" height="5" rx="1"/><rect x="9" y="9" width="5" height="5" rx="1"/>
  </svg>
}
function IconChart({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <polyline points="1.5,12 4.5,7 7.5,9 10.5,4 14.5,8"/>
  </svg>
}
function IconCards({ size = 16 }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="1.5" y="1.5" width="6" height="8" rx="1"/><rect x="8.5" y="6.5" width="6" height="8" rx="1"/>
    <rect x="1.5" y="11.5" width="6" height="3" rx="1"/><rect x="8.5" y="1.5" width="6" height="4" rx="1"/>
  </svg>
}

function IconSearch({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="11" cy="11" r="6" />
      <path d="M21 21l-4.3-4.3" />
    </svg>
  )
}
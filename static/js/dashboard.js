/* Motor Estatístico de Loterias v2.0 — Dashboard JS */

window.LOTTERY_RULES = {
  mega_sena: {label: 'Mega-Sena', total: 60, drawn: 6, min: 6, max: 15},
  lotofacil: {label: 'Lotofácil', total: 25, drawn: 15, min: 15, max: 20},
  lotomania: {label: 'Lotomania', total: 100, drawn: 20, min: 50, max: 50}
};
window.selectedLottery = 'mega_sena';

/* ────────────────────────────────────────────
   Navigation
──────────────────────────────────────────── */
function showSection(id, btn) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(n => n.classList.remove('active'));
  document.getElementById('sec-' + id).classList.add('active');
  btn.classList.add('active');
  if (id === 'analise' && !window._analiseLoaded) refreshDashboard();
}

/* ────────────────────────────────────────────
   Utils
──────────────────────────────────────────── */
async function apiFetch(url) {
  const r = await fetch(url);
  if (!r.ok) {
    let message = `HTTP ${r.status}`;
    try {
      const body = await r.json();
      message = body.detail || body.error || message;
    } catch (_) { /* resposta sem JSON */ }
    throw new Error(message);
  }
  return r.json();
}

function spinner() {
  return `<div class="loading-state"><span class="spinner"></span> Calculando…</div>`;
}

function selectLottery(element, slug) {
  if (!window.LOTTERY_RULES[slug]) return;
  window.selectedLottery = slug;
  document.querySelectorAll('.lottery-item[data-loteria]').forEach(item => item.classList.remove('active'));
  element.classList.add('active');
  document.getElementById('panel-lottery').value = slug;
  const rules = window.LOTTERY_RULES[slug];
  const input = document.getElementById('g-dezenas');
  input.min = rules.min;
  input.max = rules.max;
  input.value = rules.min;
  if (typeof buildQuickGrid === 'function') buildQuickGrid();
  window._analiseLoaded = false;
  refreshDashboard();
}

/* ────────────────────────────────────────────
   Análise Estatística
──────────────────────────────────────────── */
async function loadAnalise() {
  window._analiseLoaded = true;
  ['tbl-freq', 'tbl-score', 'tbl-atraso'].forEach(id => {
    document.getElementById(id).innerHTML = spinner();
  });

  try {
    const d = await apiFetch(`/api/analise?loteria=${window.selectedLottery}&quantidade=30`);

    // Stats
    document.getElementById('st-concursos').textContent = d.total_concursos;
    document.getElementById('st-soma').textContent      = d.soma.media;
    document.getElementById('st-desvio').textContent    = d.soma.desvio;
    document.getElementById('st-p25p75').textContent    = `${d.soma.p25} / ${d.soma.p75}`;

    // Frequência
    const maxF = Math.max(...d.frequencia.map(r => r.ocorrencias));
    document.getElementById('tbl-freq').innerHTML = `
      <table class="data-table">
        <thead><tr><th>#</th><th>Dezena</th><th>Ocorrências</th><th style="width:120px">Barra</th></tr></thead>
        <tbody>${d.frequencia.map((r, i) => `
          <tr>
            <td><span class="badge badge-green">${i + 1}</span></td>
            <td><strong>${r.dezena}</strong></td>
            <td>${r.ocorrencias}</td>
            <td>
              <div class="bar-wrap">
                <div class="bar"><div class="bar-fill" style="width:${(r.ocorrencias/maxF*100).toFixed(1)}%"></div></div>
              </div>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>`;

    // Score
    const maxS = Math.max(...d.score.map(r => r.score));
    document.getElementById('tbl-score').innerHTML = `
      <table class="data-table">
        <thead><tr><th>Rank</th><th>Dezena</th><th>Score</th><th style="width:120px">Barra</th></tr></thead>
        <tbody>${d.score.map(r => `
          <tr>
            <td><span class="badge badge-gold">${r.ranking}</span></td>
            <td><strong>${r.dezena}</strong></td>
            <td>${r.score.toFixed(4)}</td>
            <td>
              <div class="bar-wrap">
                <div class="bar"><div class="bar-fill gold" style="width:${(r.score/maxS*100).toFixed(1)}%"></div></div>
              </div>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>`;

    // Atraso
    const maxA = Math.max(...d.atraso.map(r => r.concursos));
    document.getElementById('tbl-atraso').innerHTML = `
      <table class="data-table">
        <thead><tr><th>#</th><th>Dezena</th><th>Concursos sem sair</th><th style="width:160px">Barra</th></tr></thead>
        <tbody>${d.atraso.map((r, i) => `
          <tr>
            <td><span class="badge badge-blue">${i + 1}</span></td>
            <td><strong>${r.dezena}</strong></td>
            <td>${r.concursos}</td>
            <td>
              <div class="bar-wrap">
                <div class="bar"><div class="bar-fill blue" style="width:${maxA > 0 ? (r.concursos/maxA*100).toFixed(1) : 0}%"></div></div>
              </div>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>`;

  } catch (e) {
    ['tbl-freq', 'tbl-score', 'tbl-atraso'].forEach(id => {
      document.getElementById(id).innerHTML =
        `<div style="color:var(--red);padding:16px">Erro: ${e.message}</div>`;
    });
  }
}

/* ────────────────────────────────────────────
   Gerar Jogos
──────────────────────────────────────────── */
async function gerarJogos() {
  const metodo  = document.getElementById('g-metodo').value;
  const dezenas = document.getElementById('g-dezenas').value;
  const jogos   = document.getElementById('g-jogos').value;
  const btn     = document.getElementById('btn-gerar');
  const out     = document.getElementById('jogos-output');
  const label   = document.getElementById('g-metodo-label');

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> Gerando…`;
  out.innerHTML = spinner();

  try {
    const d = await apiFetch(`/api/gerar?metodo=${metodo}&dezenas=${dezenas}&jogos=${jogos}&loteria=${window.selectedLottery}&quantidade=30`);
    label.textContent = `Método: ${d.metodo} · ${d.dezenas} dezenas · concurso #${d.ultimo_concurso}`;

    const cores = ['#3fb950','#e3b341','#58a6ff','#f85149','#bc8cff','#ff7b72'];

    out.innerHTML = `<div class="jogos-grid">${d.jogos.map((bolas, i) => `
      <div class="jogo-card">
        <div class="jogo-num">Jogo ${i + 1}</div>
        <div class="bolas">${bolas.map(b => `
          <div class="bola" style="background:${cores[i % cores.length]}">${b}</div>
        `).join('')}</div>
      </div>`).join('')}
    </div>`;
  } catch (e) {
    out.innerHTML = `<div style="color:var(--red);padding:16px">Erro: ${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '🎲 Gerar';
  }
}

/* ────────────────────────────────────────────
   Monte Carlo
──────────────────────────────────────────── */
async function simular() {
  const n   = document.getElementById('mc-n').value;
  const btn = document.getElementById('btn-mc');
  const res = document.getElementById('mc-resumo');
  const dis = document.getElementById('mc-dist');

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> Simulando…`;
  res.innerHTML = spinner();
  dis.innerHTML = spinner();

  try {
    const d = await apiFetch(`/api/simular?n=${n}&loteria=${window.selectedLottery}&quantidade=30`);

    res.innerHTML = `
      <table class="data-table">
        <tbody>
          <tr><td style="color:var(--text-dim)">Total simulações</td><td><strong>${d.total}</strong></td></tr>
          <tr><td style="color:var(--text-dim)">Média de acertos</td><td><strong style="color:var(--green)">${d.media}</strong></td></tr>
          <tr><td style="color:var(--text-dim)">Máximo acertos</td><td><strong style="color:var(--gold)">${d.maximo}</strong></td></tr>
          <tr><td style="color:var(--text-dim)">Mínimo acertos</td><td><strong>${d.minimo}</strong></td></tr>
          <tr><td style="color:var(--text-dim)">Desvio padrão</td><td><strong style="color:var(--blue)">${d.desvio}</strong></td></tr>
        </tbody>
      </table>`;

    const entries = Object.entries(d.distribuicao);
    const maxPct  = Math.max(...entries.map(([, v]) => v));

    dis.innerHTML = entries.map(([k, v]) => `
      <div class="dist-row">
        <div class="dist-key">${k} acertos</div>
        <div class="bar" style="flex:1">
          <div class="bar-fill" style="width:${(v / maxPct * 100).toFixed(1)}%"></div>
        </div>
        <div class="dist-val">${v.toFixed(2)}%</div>
      </div>`).join('');

  } catch (e) {
    res.innerHTML = dis.innerHTML =
      `<div style="color:var(--red)">Erro: ${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '▶ Executar';
  }
}

/* ────────────────────────────────────────────
   Testes Estatísticos
──────────────────────────────────────────── */
async function rodarTestes() {
  const btn = document.getElementById('btn-testes');
  const out = document.getElementById('testes-output');

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> Calculando…`;
  out.innerHTML = spinner();

  try {
    const d = await apiFetch(`/api/testes?loteria=${window.selectedLottery}&quantidade=30`);
    const chi  = d.chi_quadrado;
    const ks   = d.kolmogorov_smirnov;
    const runs = d.runs;

    out.innerHTML = `
      <div class="teste-block">
        <h4>1. Qui-Quadrado (χ²)</h4>
        <div class="teste-row">
          <div class="teste-item"><label>Estatística χ²</label><div class="val">${chi.chi2 ?? '—'}</div></div>
          <div class="teste-item"><label>p-value</label><div class="val">${typeof chi.p_value === 'number' ? chi.p_value.toFixed(4) : '—'}</div></div>
        </div>
        <div class="teste-conclusao">→ ${chi.conclusao || '—'}</div>
      </div>

      <div class="teste-block">
        <h4>2. Kolmogorov-Smirnov</h4>
        <div class="teste-row">
          <div class="teste-item"><label>Estatística D</label><div class="val">${ks.statistic ?? '—'}</div></div>
          <div class="teste-item"><label>p-value</label><div class="val">${typeof ks.p_value === 'number' ? ks.p_value.toFixed(4) : '—'}</div></div>
        </div>
        <div class="teste-conclusao">→ ${ks.interpretacao || '—'}</div>
      </div>

      <div class="teste-block">
        <h4>3. Teste de Runs (Dezena 1)</h4>
        <div class="teste-row">
          <div class="teste-item"><label>Z-score</label><div class="val">${runs.z_score ?? '—'}</div></div>
        </div>
        <div class="teste-conclusao">→ ${runs.interpretacao || '—'}</div>
      </div>`;

  } catch (e) {
    out.innerHTML = `<div style="color:var(--red);padding:16px">Erro: ${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '▶ Executar Testes';
  }
}

/* ── Resultados oficiais e carga inicial ── */
async function loadResultados(forceUpdate = false) {
  const status = document.getElementById('resultados-status');
  const output = document.getElementById('resultados-list');
  if (!status || !output) return;
  output.innerHTML = spinner();
  try {
    const atualizar = forceUpdate ? '&atualizar=true' : '';
    const d = await apiFetch(`/api/resultados?loteria=${window.selectedLottery}&quantidade=5${atualizar}`);
    const meta = d.fonte_dados || {};
    const cacheInfo = meta.cache_desatualizado
      ? 'cache desatualizado (CAIXA indisponível)'
      : (meta.cache ? 'cache local' : 'consulta CAIXA');
    status.textContent = `${window.LOTTERY_RULES[window.selectedLottery].label} · último concurso #${d.ultimo_concurso} · ${cacheInfo}`;
    if (meta.aviso) status.textContent += ` · ${meta.aviso}`;
    output.innerHTML = d.resultados.map(item => {
      const data = new Date(`${item.data}T00:00:00Z`).toLocaleDateString('pt-BR', {timeZone: 'UTC'});
      const bolas = item.dezenas.map(n => `<span class="resultado-bola">${String(n).padStart(2, '0')}</span>`).join('');
      return `<div class="resultado-item"><div class="resultado-cabecalho"><strong>Concurso #${item.concurso}</strong><span>${data}</span></div><div class="resultado-dezenas">${bolas}</div></div>`;
    }).join('');
  } catch (error) {
    status.textContent = 'Não foi possível atualizar os resultados oficiais.';
    output.textContent = error.message;
  }
}

async function refreshDashboard(forceUpdate = false) {
  await loadAnalise();
  await loadResultados(forceUpdate);
}

window.addEventListener('DOMContentLoaded', refreshDashboard);

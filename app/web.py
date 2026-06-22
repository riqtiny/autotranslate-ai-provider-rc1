"""Self-contained translation comparison web UI."""

TRANSLATION_LAB_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Translation Model Comparison</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
      color-scheme: dark;
      --bg: #171613;
      --panel: #211f1a;
      --panel-2: #29261f;
      --line: rgba(238, 228, 204, 0.14);
      --text: #f0eadc;
      --muted: #a9a08e;
      --soft: #746c5d;
      --accent: #c9a24f;
      --accent-2: #806b3b;
      --danger: #d06b5d;
      --ok: #78a977;
      --shadow: rgba(8, 7, 5, 0.32);
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      min-height: 100dvh;
      background:
        radial-gradient(circle at 78% 8%, rgba(201, 162, 79, 0.16), transparent 24rem),
        radial-gradient(circle at 8% 62%, rgba(128, 107, 59, 0.18), transparent 22rem),
        linear-gradient(145deg, #171613 0%, #11100e 100%);
      color: var(--text);
      font-family: Outfit, ui-sans-serif, sans-serif;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.24;
      background-image:
        linear-gradient(rgba(238, 228, 204, 0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(238, 228, 204, 0.035) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, black, transparent 85%);
    }

    button, input, select, textarea { font: inherit; }
    button {
      border: 0;
      color: inherit;
      cursor: pointer;
      transition: transform 180ms cubic-bezier(.16, 1, .3, 1), border-color 180ms, background 180ms;
    }
    button:active { transform: translateY(1px) scale(0.99); }
    button:disabled { cursor: not-allowed; opacity: 0.52; }

    .shell {
      width: min(1460px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 56px;
    }

    .hero {
      min-height: min(820px, 100dvh);
      display: grid;
      grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
      gap: 28px;
      align-items: stretch;
    }

    .intro {
      border: 1px solid var(--line);
      background: rgba(33, 31, 26, 0.72);
      box-shadow: 0 22px 70px var(--shadow), inset 0 1px 0 rgba(255,255,255,0.06);
      border-radius: 34px;
      padding: clamp(28px, 4vw, 64px);
      position: relative;
      overflow: hidden;
    }

    .intro::after {
      content: "";
      position: absolute;
      right: -120px;
      top: 14%;
      width: 320px;
      height: 320px;
      border: 1px solid rgba(201, 162, 79, 0.26);
      border-radius: 50%;
      box-shadow: inset 0 0 0 42px rgba(201, 162, 79, 0.03);
      animation: drift 9s ease-in-out infinite alternate;
    }

    .kicker {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font: 600 12px JetBrains Mono, monospace;
      margin-bottom: 42px;
    }
    .kicker::before {
      content: "";
      width: 34px;
      height: 1px;
      background: var(--accent);
    }

    h1 {
      margin: 0;
      max-width: 11ch;
      font-size: clamp(44px, 7vw, 104px);
      line-height: 0.88;
      letter-spacing: -0.065em;
      font-weight: 800;
    }

    .lede {
      margin: 28px 0 0;
      max-width: 68ch;
      color: var(--muted);
      font-size: clamp(16px, 1.4vw, 20px);
      line-height: 1.65;
    }

    .control-panel {
      border: 1px solid var(--line);
      border-radius: 34px;
      background: rgba(22, 21, 18, 0.76);
      box-shadow: 0 22px 70px var(--shadow), inset 0 1px 0 rgba(255,255,255,0.06);
      padding: 22px;
      align-self: end;
    }

    .field { display: grid; gap: 8px; margin-bottom: 16px; }
    label {
      color: var(--text);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      font-weight: 700;
    }
    .help { color: var(--soft); font-size: 13px; line-height: 1.45; }
    input, select {
      width: 100%;
      min-height: 46px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: #151410;
      color: var(--text);
      padding: 0 14px;
      outline: none;
    }
    input:focus, select:focus { border-color: rgba(201, 162, 79, 0.72); }

    .button-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .primary, .secondary {
      min-height: 48px;
      border-radius: 16px;
      font-weight: 800;
    }
    .primary { background: var(--accent); color: #1a160d; }
    .secondary { background: transparent; border: 1px solid var(--line); }
    .secondary:hover { border-color: rgba(201, 162, 79, 0.48); }

    .status-strip {
      margin-top: 18px;
      display: grid;
      gap: 10px;
      font: 12px JetBrains Mono, monospace;
      color: var(--muted);
    }
    .pulse {
      display: inline-block;
      width: 7px;
      height: 7px;
      border-radius: 99px;
      background: var(--ok);
      margin-right: 8px;
      animation: breathe 1.8s ease-in-out infinite;
    }

    .workbench {
      margin-top: 28px;
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      gap: 28px;
      align-items: start;
    }

    .language-rail, .results, .metrics {
      border: 1px solid var(--line);
      border-radius: 30px;
      background: rgba(33, 31, 26, 0.76);
      box-shadow: 0 18px 60px var(--shadow), inset 0 1px 0 rgba(255,255,255,0.05);
    }

    .language-rail { padding: 18px; position: sticky; top: 18px; }
    .rail-head { display: flex; justify-content: space-between; gap: 16px; align-items: baseline; margin-bottom: 14px; }
    .rail-head h2, .section-title h2 { margin: 0; font-size: 17px; letter-spacing: -0.02em; }
    .count { color: var(--accent); font: 600 12px JetBrains Mono, monospace; }

    .language-list { display: grid; gap: 8px; }
    .language-item {
      display: grid;
      grid-template-columns: 46px 1fr;
      gap: 12px;
      align-items: center;
      width: 100%;
      min-height: 58px;
      padding: 8px;
      border-radius: 18px;
      border: 1px solid transparent;
      background: transparent;
      text-align: left;
    }
    .language-item.active, .language-item:hover {
      background: rgba(201, 162, 79, 0.08);
      border-color: rgba(201, 162, 79, 0.2);
    }
    .code {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 14px;
      background: #151410;
      color: var(--accent);
      font: 700 12px JetBrains Mono, monospace;
      text-transform: uppercase;
    }
    .language-item strong { display: block; font-size: 14px; }
    .language-item span { display: block; color: var(--muted); font-size: 12px; margin-top: 2px; }

    .main-stack { display: grid; gap: 28px; }
    .metrics { padding: 18px; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
    .metric {
      border-top: 1px solid var(--line);
      padding-top: 12px;
      min-height: 82px;
    }
    .metric span { color: var(--muted); font-size: 12px; }
    .metric strong { display: block; margin-top: 8px; font: 600 21px JetBrains Mono, monospace; letter-spacing: -0.04em; }

    .results { padding: 20px; min-height: 420px; }
    .section-title {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: baseline;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--line);
    }
    .section-title p { margin: 0; color: var(--muted); font-size: 13px; }

    .result-grid { display: grid; gap: 12px; margin-top: 16px; }
    .result-card {
      display: grid;
      grid-template-columns: minmax(160px, 0.26fr) minmax(0, 1fr) minmax(120px, 0.18fr);
      gap: 18px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: rgba(16, 15, 13, 0.55);
      animation: rise 520ms cubic-bezier(.16, 1, .3, 1) both;
      animation-delay: calc(var(--i, 0) * 40ms);
    }
    .result-card h3 { margin: 0; font-size: 15px; }
    .result-card small { display: block; color: var(--muted); margin-top: 5px; font: 12px JetBrains Mono, monospace; }
    .source { color: var(--muted); line-height: 1.45; }
    .translation { color: var(--text); line-height: 1.55; }
    .ref-line { color: var(--soft); font-size: 12px; margin-top: 6px; }
    .ref-line b { color: var(--muted); font-weight: 600; }
    .bad { color: var(--danger); }
    .ok { color: var(--ok); }

    .toggle-field { margin-bottom: 16px; }
    .toggle { display: flex; align-items: center; gap: 10px; text-transform: none; letter-spacing: normal; font-weight: 600; cursor: pointer; }
    .toggle input { width: auto; min-height: 0; accent-color: var(--accent); }

    .score-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .badge {
      display: inline-flex;
      align-items: baseline;
      gap: 5px;
      padding: 3px 9px;
      border-radius: 99px;
      border: 1px solid var(--line);
      background: rgba(201, 162, 79, 0.06);
      font: 600 11px JetBrains Mono, monospace;
    }
    .badge i { font-style: normal; color: var(--soft); text-transform: uppercase; letter-spacing: 0.06em; }
    .badge b { color: var(--accent); font-weight: 700; }

    .leaderboard { padding: 20px; }
    .lb-table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
    .lb-table th, .lb-table td { text-align: right; padding: 11px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }
    .lb-table th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 700; }
    .lb-table th:first-child, .lb-table td:first-child { text-align: left; }
    .lb-table td:first-child { color: var(--text); font-weight: 600; }
    .lb-table td.num { font: 600 14px JetBrains Mono, monospace; }
    .lb-table tbody tr:hover { background: rgba(201, 162, 79, 0.05); }
    .lb-table td.best { color: var(--ok); }
    .lb-note { margin-top: 12px; color: var(--soft); font-size: 12px; line-height: 1.5; }
    .lb-note.warn { color: #d7a69f; }

    .metric-info { margin-top: 14px; border: 1px solid var(--line); border-radius: 16px; background: rgba(16, 15, 13, 0.4); padding: 10px 16px; }
    .metric-info summary { cursor: pointer; font-weight: 700; color: var(--accent); font-size: 13px; }
    .metric-info ul { margin: 12px 0 4px; padding-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px; }
    .metric-info li { margin-bottom: 8px; }
    .metric-info b { color: var(--text); }

    .empty, .error-box, .loading-box {
      min-height: 260px;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
    }
    .empty strong, .error-box strong, .loading-box strong {
      display: block;
      color: var(--text);
      margin-bottom: 8px;
      font-size: 18px;
    }
    .error-box { color: #d7a69f; }
    .skeleton {
      width: min(520px, 100%);
      display: grid;
      gap: 14px;
    }
    .skeleton i {
      display: block;
      height: 66px;
      border-radius: 18px;
      background: linear-gradient(90deg, rgba(255,255,255,0.04), rgba(201,162,79,0.12), rgba(255,255,255,0.04));
      background-size: 220% 100%;
      animation: shimmer 1.4s ease-in-out infinite;
    }

    .footnote {
      margin: 24px 0 0;
      color: var(--soft);
      font-size: 12px;
      line-height: 1.6;
      max-width: 78ch;
    }

    @keyframes drift { to { transform: translate3d(-28px, 18px, 0) scale(1.06); } }
    @keyframes breathe { 50% { transform: scale(1.8); opacity: 0.36; } }
    @keyframes shimmer { to { background-position: -220% 0; } }
    @keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }

    @media (max-width: 980px) {
      .hero, .workbench { grid-template-columns: 1fr; }
      .language-rail { position: static; }
      .metrics { grid-template-columns: repeat(2, 1fr); }
      .result-card { grid-template-columns: 1fr; }
    }
    @media (max-width: 620px) {
      .shell { width: min(100% - 20px, 1460px); padding-top: 10px; }
      .intro, .control-panel, .language-rail, .results, .metrics { border-radius: 22px; }
      .button-row, .metrics { grid-template-columns: 1fr; }
      h1 { font-size: clamp(42px, 17vw, 72px); }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="intro">
        <div class="kicker">Colab translation bench</div>
        <h1>Compare models into Indonesian.</h1>
        <p class="lede">Run every supported API model against ten high-traffic source languages. Switch loaded model before each session, send correct language codes per family, then record RAM, VRAM, tokens, latency, and output quality side by side.</p>
      </div>

      <aside class="control-panel" aria-label="Translation controls">
        <div class="field">
          <label for="apiKey">API key</label>
          <input id="apiKey" type="password" autocomplete="off" placeholder="Only needed when CT2_API_KEY is set" />
          <div class="help">Stored in this browser tab only. Sent as Bearer token.</div>
        </div>
        <div class="field">
          <label for="modelSelect">Active model</label>
          <select id="modelSelect"></select>
          <div class="help">Changing selection calls <code>/admin/switch/{model}</code>.</div>
        </div>
        <div class="field toggle-field">
          <label class="toggle">
            <input id="cometToggle" type="checkbox" />
            <span>Score COMET (neural, slower)</span>
          </label>
          <div class="help">BLEU &amp; ChrF++ are always scored. COMET needs <code>requirements-metrics.txt</code>.</div>
        </div>
        <div class="button-row">
          <button id="runSelected" class="primary">Run selected</button>
          <button id="runAll" class="secondary">Compare all</button>
        </div>
        <div class="status-strip">
          <div><span class="pulse"></span><span id="liveState">Booting interface</span></div>
          <div id="loadedState">Loaded model: unknown</div>
          <div id="modelCount">Models: unknown</div>
        </div>
      </aside>
    </section>

    <section class="workbench">
      <aside class="language-rail">
        <div class="rail-head">
          <h2>Source set</h2>
          <span class="count">10 langs</span>
        </div>
        <div id="languageList" class="language-list"></div>
      </aside>

      <div class="main-stack">
        <section class="metrics" aria-label="Machine resource stats">
          <div class="metric"><span>Loaded model</span><strong id="metricLoaded">none</strong></div>
          <div class="metric"><span>Compute mode</span><strong id="metricMode">unknown</strong></div>
          <div class="metric"><span>VRAM used</span><strong id="metricVram">n/a</strong></div>
          <div class="metric"><span>RAM used</span><strong id="metricRam">n/a</strong></div>
          <div class="metric"><span>Throughput</span><strong id="metricTps">n/a</strong></div>
          <div class="metric"><span>Session time</span><strong id="metricTime">0.0s</strong></div>
        </section>

        <section class="results leaderboard" id="leaderboardSection" hidden>
          <div class="section-title">
            <div>
              <h2>Model leaderboard</h2>
              <p id="leaderboardMeta">Quality &amp; cost per model. Higher BLEU / ChrF++ / COMET is better.</p>
            </div>
          </div>
          <details class="metric-info">
            <summary>What do these metrics measure?</summary>
            <ul>
              <li><b>BLEU / SacreBLEU</b> — n-gram precision overlap between the translation and the reference (0–100). SacreBLEU is the standardized, reproducible implementation, so scores are comparable across runs and papers.</li>
              <li><b>ChrF++</b> — character n-gram F-score plus word bigrams. It rewards partial-word matches and is more robust than BLEU on short sentences and morphologically rich languages (0–100).</li>
              <li><b>COMET</b> — a neural metric (XLM-R based) trained on human ratings. It judges meaning/adequacy from source + hypothesis + reference (~0–1) and correlates best with human judgement, but is heavier to run.</li>
              <li><b>Tok/s</b> — decoding throughput: completion tokens ÷ latency. <b>VRAM</b> (GPU mode) or <b>RAM</b> (CPU mode) shows the memory the run used.</li>
            </ul>
          </details>
          <div id="leaderboard"></div>
        </section>

        <section class="results">
          <div class="section-title">
            <div>
              <h2>Translation output</h2>
              <p id="resultMeta">No run yet. Pick model, then run selected or compare all.</p>
            </div>
          </div>
          <div id="results" class="empty">
            <div><strong>Empty bench.</strong><span>Results appear here after translation session.</span></div>
          </div>
        </section>
      </div>
    </section>

    <p class="footnote">Model families handled client-side: TranslateGemma uses ISO 639-1 codes, NLLB uses FLORES-200 codes, and chat models use explicit translation prompts. Target language always Indonesian.</p>
  </main>

  <script>
    // `ref` is the gold Indonesian translation used to score BLEU / ChrF++ / COMET.
    const LANGUAGES = [
      { name: 'English', iso: 'en', flores: 'eng_Latn', sample: 'The weather is beautiful today.', ref: 'Cuaca hari ini indah.' },
      { name: 'Mandarin Chinese', iso: 'zh', flores: 'zho_Hans', sample: '今天的天气很好，我们去市场吧。', ref: 'Cuaca hari ini sangat bagus, ayo kita pergi ke pasar.' },
      { name: 'Hindi', iso: 'hi', flores: 'hin_Deva', sample: 'मुझे हर सुबह गरम चाय पीना पसंद है।', ref: 'Saya suka minum teh panas setiap pagi.' },
      { name: 'Spanish', iso: 'es', flores: 'spa_Latn', sample: 'Me gusta mucho la comida picante.', ref: 'Saya sangat suka makanan pedas.' },
      { name: 'French', iso: 'fr', flores: 'fra_Latn', sample: 'Le chat dort sur le canapé.', ref: 'Kucing itu tidur di sofa.' },
      { name: 'Arabic', iso: 'ar', flores: 'arb_Arab', sample: 'الكتاب الجديد على الطاولة في الغرفة.', ref: 'Buku baru itu ada di atas meja di dalam kamar.' },
      { name: 'Bengali', iso: 'bn', flores: 'ben_Beng', sample: 'আজ বিকেলে আমরা নদীর ধারে হাঁটব।', ref: 'Sore ini kami akan berjalan di tepi sungai.' },
      { name: 'Russian', iso: 'ru', flores: 'rus_Cyrl', sample: 'Я изучаю программирование уже два года.', ref: 'Saya sudah belajar pemrograman selama dua tahun.' },
      { name: 'Portuguese', iso: 'pt', flores: 'por_Latn', sample: 'A reunião começa depois do almoço.', ref: 'Rapat dimulai setelah makan siang.' },
      { name: 'Urdu', iso: 'ur', flores: 'urd_Arab', sample: 'یہ شہر رات کے وقت بہت خوبصورت لگتا ہے۔', ref: 'Kota ini terlihat sangat indah di malam hari.' }
    ];

    const els = {
      apiKey: document.getElementById('apiKey'),
      modelSelect: document.getElementById('modelSelect'),
      runSelected: document.getElementById('runSelected'),
      runAll: document.getElementById('runAll'),
      liveState: document.getElementById('liveState'),
      loadedState: document.getElementById('loadedState'),
      modelCount: document.getElementById('modelCount'),
      languageList: document.getElementById('languageList'),
      results: document.getElementById('results'),
      resultMeta: document.getElementById('resultMeta'),
      metricLoaded: document.getElementById('metricLoaded'),
      metricMode: document.getElementById('metricMode'),
      metricVram: document.getElementById('metricVram'),
      metricRam: document.getElementById('metricRam'),
      metricTps: document.getElementById('metricTps'),
      metricTime: document.getElementById('metricTime'),
      cometToggle: document.getElementById('cometToggle'),
      leaderboardSection: document.getElementById('leaderboardSection'),
      leaderboard: document.getElementById('leaderboard'),
      leaderboardMeta: document.getElementById('leaderboardMeta')
    };

    let models = [];
    let modelInfo = new Map();
    let selectedLanguage = LANGUAGES[0].name;

    function headers() {
      const h = { 'Content-Type': 'application/json' };
      const key = els.apiKey.value.trim();
      if (key) h.Authorization = `Bearer ${key}`;
      return h;
    }

    async function api(path, options = {}) {
      const res = await fetch(path, { ...options, headers: { ...headers(), ...(options.headers || {}) } });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${text}`);
      }
      return res.json();
    }

    function familyOf(model) {
      const info = modelInfo.get(model);
      if (info && info.family) return info.family;
      if (model.includes('translategemma')) return 'translategemma';
      if (model.includes('nllb')) return 'nllb';
      if (model.includes('gemma')) return 'gemma';
      if (model.includes('qwen')) return 'qwen';
      return 'chat';
    }

    function requestFor(model, lang) {
      const family = familyOf(model);
      let content = lang.sample;
      const body = {
        model,
        messages: [{ role: 'user', content }],
        max_tokens: 96,
        temperature: 0
      };

      if (family === 'nllb') {
        body.source_lang = lang.flores;
        body.target_lang = 'ind_Latn';
      } else if (family === 'translategemma') {
        body.source_lang = lang.iso;
        body.target_lang = 'id';
      }  else {
        body.messages[0].content = `Translate this ${lang.name} sentence to Indonesian. Return only Indonesian translation.\n\n${lang.sample}`;
      }
      return body;
    }

    function renderLanguages() {
      els.languageList.innerHTML = LANGUAGES.map(lang => `
        <button class="language-item ${lang.name === selectedLanguage ? 'active' : ''}" data-language="${lang.name}">
          <span class="code">${lang.iso}</span>
          <span><strong>${lang.name}</strong><span>${lang.flores}</span></span>
        </button>
      `).join('');
      [...els.languageList.querySelectorAll('button')].forEach(btn => {
        btn.addEventListener('click', () => {
          selectedLanguage = btn.dataset.language;
          renderLanguages();
        });
      });
    }

    function setBusy(busy, label) {
      els.runSelected.disabled = busy;
      els.runAll.disabled = busy;
      els.modelSelect.disabled = busy;
      els.liveState.textContent = label;
    }

    function fmtMiB(value) {
      if (value === undefined || value === null) return 'n/a';
      return `${Math.round(value).toLocaleString()} MiB`;
    }

    function updateStats(status, seconds = 0) {
      const vram = status?.vram || {};
      const ram = status?.ram || {};
      // GPU mode is detected from VRAM stats (empty {} when running on CPU).
      const onGpu = vram.used_mib !== undefined;
      els.metricLoaded.textContent = status?.loaded_model || 'none';
      els.metricMode.textContent = onGpu
        ? `GPU · ${vram.device || status?.device || 'cuda'}`
        : `CPU · ${status?.device || 'cpu'}`;
      els.metricVram.textContent = onGpu ? fmtMiB(vram.used_mib) : 'n/a (CPU)';
      els.metricRam.textContent = ram.used_mib !== undefined ? fmtMiB(ram.used_mib) : 'n/a';
      els.metricTime.textContent = `${seconds.toFixed(1)}s`;
      els.loadedState.textContent = `Loaded model: ${status?.loaded_model || 'none'}`;
    }

    function showLoading(lines = 4) {
      els.results.className = 'loading-box';
      els.results.innerHTML = `<div class="skeleton">${Array.from({ length: lines }, () => '<i></i>').join('')}</div>`;
    }

    function showError(error) {
      els.results.className = 'error-box';
      els.results.innerHTML = `<div><strong>Run failed.</strong><span>${escapeHtml(error.message)}</span></div>`;
      els.resultMeta.textContent = 'Error returned by API. Check conversion, API key, or model support.';
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>'"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));
    }

    function renderResults(rows, startedAt, endedStatus) {
      const seconds = (performance.now() - startedAt) / 1000;
      updateStats(endedStatus, seconds);
      els.metricTps.textContent = fmtTps(avg(rows.map(r => r.tps)));
      els.results.className = 'result-grid';
      els.resultMeta.textContent = `${rows.length} translations complete across ${new Set(rows.map(r => r.model)).size} model session(s).`;
      els.results.innerHTML = rows.map((row, i) => `
        <article class="result-card" style="--i:${i}">
          <div>
            <h3>${escapeHtml(row.language)}</h3>
            <small>${escapeHtml(row.model)} · ${escapeHtml(row.family)}</small>
          </div>
          <div>
            <div class="source">${escapeHtml(row.source)}</div>
            <div class="translation ${row.error ? 'bad' : 'ok'}">${escapeHtml(row.translation || row.error)}</div>
            ${row.ref ? `<div class="ref-line"><b>ref:</b> ${escapeHtml(row.ref)}</div>` : ''}
          </div>
          <div>
            <small>${row.ms} ms</small><small>${row.tokens} tokens</small><small>${fmtTps(row.tps)}</small>
            ${badgesHtml(row.scores)}
          </div>
        </article>
      `).join('');
    }

    function avg(values) {
      const v = values.filter(x => x !== null && x !== undefined && isFinite(x));
      return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
    }

    function fmtTps(value) {
      return (value === null || value === undefined || !isFinite(value)) ? '— tok/s' : `${value.toFixed(1)} tok/s`;
    }

    function fmtScore(value) {
      return (value === undefined || value === null) ? '—' : Number(value).toFixed(2);
    }

    // Per-row metric chips. `scores` = { bleu, chrf, comet? } once /metrics/score returns.
    function badgesHtml(scores) {
      if (!scores) return '';
      const chips = [
        `<span class="badge"><i>bleu</i><b>${fmtScore(scores.bleu)}</b></span>`,
        `<span class="badge"><i>chrf++</i><b>${fmtScore(scores.chrf)}</b></span>`
      ];
      if (scores.comet !== undefined) {
        chips.push(`<span class="badge"><i>comet</i><b>${fmtScore(scores.comet)}</b></span>`);
      }
      return `<div class="score-badges">${chips.join('')}</div>`;
    }

    async function refresh() {
      const [modelList, status] = await Promise.all([
        api('/v1/models'),
        api('/admin/status')
      ]);
      models = modelList.data.map(m => m.id);
      modelInfo = new Map((status.models || []).map(m => [m.id, m]));
      els.modelSelect.innerHTML = models.map(id => `<option value="${id}">${id}</option>`).join('');
      if (status.loaded_model && models.includes(status.loaded_model)) els.modelSelect.value = status.loaded_model;
      els.modelCount.textContent = `Models: ${models.length}`;
      els.liveState.textContent = 'Ready';
      updateStats(status, 0);
    }

    async function switchModel(model) {
      els.liveState.textContent = `Switching ${model}`;
      const status = await api(`/admin/switch/${encodeURIComponent(model)}`, { method: 'POST' });
      els.loadedState.textContent = `Loaded model: ${status.loaded_model || model}`;
    }

    async function translateOne(model, lang) {
      const t0 = performance.now();
      try {
        const body = await api('/v1/chat/completions', {
          method: 'POST',
          body: JSON.stringify(requestFor(model, lang))
        });
        const usage = body.usage || {};
        const ms = Math.round(performance.now() - t0);
        const completion = usage.completion_tokens ?? 0;
        // Throughput = decoded tokens / wall-clock seconds (network + decode).
        const tps = ms > 0 && completion ? completion / (ms / 1000) : null;
        return {
          model,
          family: familyOf(model),
          language: lang.name,
          source: lang.sample,
          ref: lang.ref,
          translation: body.choices?.[0]?.message?.content || '',
          tokens: usage.total_tokens ?? 'n/a',
          completion,
          tps,
          ms
        };
      } catch (error) {
        return {
          model,
          family: familyOf(model),
          language: lang.name,
          source: lang.sample,
          ref: lang.ref,
          error: error.message,
          tokens: 'n/a',
          tps: null,
          ms: Math.round(performance.now() - t0)
        };
      }
    }

    // Score one model's translations and build its leaderboard row. BLEU/ChrF++
    // are always computed; COMET only when toggled (and installed server-side).
    async function scoreModel(model, modelRows, wantComet) {
      const ok = modelRows.filter(r => !r.error && r.translation && r.ref);
      const entry = {
        model,
        family: familyOf(model),
        avgMs: Math.round(modelRows.reduce((a, r) => a + (r.ms || 0), 0) / modelRows.length),
        avgTps: avg(modelRows.map(r => r.tps)),
        tokens: modelRows.reduce((a, r) => a + (Number(r.tokens) || 0), 0),
        scored: ok.length,
        total: modelRows.length,
        system: {},
        available: null,
        cometModel: null,
        error: null
      };
      if (!ok.length) { entry.error = 'no scorable rows'; return entry; }
      try {
        const res = await api('/metrics/score', {
          method: 'POST',
          body: JSON.stringify({
            model,
            comet: wantComet,
            segments: ok.map(r => ({ src: r.source, mt: r.translation, ref: r.ref }))
          })
        });
        entry.available = res.available;
        entry.system = res.system || {};
        entry.cometModel = res.comet_model;
        entry.errors = res.errors || {};
        ok.forEach((r, i) => { r.scores = res.segments[i] || {}; });
      } catch (error) {
        entry.error = error.message;
      }
      return entry;
    }

    function renderLeaderboard(board) {
      if (!board.length) { els.leaderboardSection.hidden = true; return; }
      els.leaderboardSection.hidden = false;
      const hasComet = board.some(e => e.system && e.system.comet !== undefined);
      const best = {};
      ['bleu', 'chrf', 'comet'].forEach(k => {
        const vals = board.map(e => e.system?.[k]).filter(v => v !== undefined && v !== null);
        if (vals.length) best[k] = Math.max(...vals);
      });
      const cell = (v, k) => {
        const isBest = v !== undefined && v !== null && best[k] !== undefined && v === best[k];
        return `<td class="num${isBest ? ' best' : ''}">${fmtScore(v)}</td>`;
      };
      const head = `<tr><th>Model</th><th>BLEU</th><th>ChrF++</th>${hasComet ? '<th>COMET</th>' : ''}<th>Tok/s</th><th>Avg ms</th><th>Tokens</th></tr>`;
      const body = board.map(e => `
        <tr>
          <td>${escapeHtml(e.model)}<br><small style="color:var(--soft);font-weight:400">${escapeHtml(e.family)} · ${e.scored}/${e.total} scored</small></td>
          ${cell(e.system?.bleu, 'bleu')}
          ${cell(e.system?.chrf, 'chrf')}
          ${hasComet ? cell(e.system?.comet, 'comet') : ''}
          <td class="num">${e.avgTps != null ? e.avgTps.toFixed(1) : '—'}</td>
          <td class="num">${e.avgMs}</td>
          <td class="num">${e.tokens}</td>
        </tr>
      `).join('');
      els.leaderboard.innerHTML = `<table class="lb-table"><thead>${head}</thead><tbody>${body}</tbody></table>${leaderboardNotes(board)}`;
      els.leaderboardMeta.textContent = `${board.length} model(s) · BLEU & ChrF++ are 0–100, COMET ~0–1. Higher is better.`;
    }

    function leaderboardNotes(board) {
      const notes = [];
      const cometAvail = board.some(e => e.available && e.available.comet);
      if (els.cometToggle.checked && !cometAvail) {
        notes.push(`<div class="lb-note warn">COMET unavailable on the server — install it with <code>pip install -r requirements-metrics.txt</code>.</div>`);
      }
      const cometModel = board.map(e => e.cometModel).find(Boolean);
      if (cometModel) notes.push(`<div class="lb-note">COMET model: <code>${escapeHtml(cometModel)}</code></div>`);
      const errs = board.filter(e => e.error).map(e => `${e.model}: ${e.error}`);
      if (errs.length) notes.push(`<div class="lb-note warn">${escapeHtml(errs.join(' · '))}</div>`);
      return notes.join('');
    }

    async function run(modelsToRun) {
      setBusy(true, 'Running translation session');
      showLoading(modelsToRun.length * LANGUAGES.length > 10 ? 8 : 4);
      const startedAt = performance.now();
      const wantComet = els.cometToggle.checked;
      const rows = [];
      const board = [];
      els.leaderboardSection.hidden = true;
      try {
        for (const model of modelsToRun) {
          await switchModel(model);
          const modelRows = [];
          for (const lang of LANGUAGES) {
            els.liveState.textContent = `${model}: ${lang.name} to Indonesian`;
            const row = await translateOne(model, lang);
            rows.push(row);
            modelRows.push(row);
            renderResults(rows, startedAt, await api('/admin/status'));
          }
          els.liveState.textContent = `${model}: scoring ${wantComet ? '(BLEU, ChrF++, COMET)' : '(BLEU, ChrF++)'}`;
          board.push(await scoreModel(model, modelRows, wantComet));
          renderResults(rows, startedAt, await api('/admin/status'));
          renderLeaderboard(board);
        }
        const endedStatus = await api('/admin/status');
        renderResults(rows, startedAt, endedStatus);
        renderLeaderboard(board);
        els.liveState.textContent = 'Session complete';
      } catch (error) {
        showError(error);
        els.liveState.textContent = 'Session failed';
      } finally {
        setBusy(false, els.liveState.textContent);
      }
    }

    els.modelSelect.addEventListener('change', async () => {
      try {
        setBusy(true, 'Switching selected model');
        await switchModel(els.modelSelect.value);
        updateStats(await api('/admin/status'), 0);
        els.liveState.textContent = 'Ready';
      } catch (error) {
        showError(error);
      } finally {
        setBusy(false, els.liveState.textContent);
      }
    });

    els.runSelected.addEventListener('click', () => run([els.modelSelect.value]));
    els.runAll.addEventListener('click', () => run(models));
    els.apiKey.addEventListener('change', async () => {
      try { await refresh(); } catch (error) { showError(error); }
    });

    renderLanguages();
    refresh().catch(error => {
      els.liveState.textContent = 'Needs API key or reachable API';
      showError(error);
    });
  </script>
</body>
</html>
"""

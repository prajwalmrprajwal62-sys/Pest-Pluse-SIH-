/* ============================================================
   PestPulse — farmer.js v2
   Auto-detect on image upload, full form logic, voice wiring
   ============================================================ */
(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────
  let currentStep = 1;
  let selectedFile = null;
  let aiDetected   = {};   // {crop, symptom_group, severity} from quick-infer
  const form = {
    crop: null, growth_stage: null, symptom_group: null,
    severity: null, recent_rain: null, trap_count: null,
    lat: 12.97, lon: 77.59,
  };

  // ── Step navigation ────────────────────────────────────────
  function goStep(n) {
    if (n === 3) buildSummary();
    [1,2,3].forEach(i => {
      document.getElementById(`step-${i}`)?.classList.toggle('hidden', i !== n);
      const si = document.getElementById(`si-${i}`);
      if (si) {
        si.classList.remove('active','complete');
        if (i < n) si.classList.add('complete');
        if (i === n) si.classList.add('active');
      }
    });
    currentStep = n;
    window.scrollTo(0, 0);
  }
  window.goStep = goStep;

  // ── Image upload & AI auto-detect ─────────────────────────
  function initUpload() {
    const zone   = document.getElementById('upload-zone');
    const input  = document.getElementById('file-input');
    if (!zone || !input) return;

    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover',  e => { e.preventDefault(); zone.style.borderColor='var(--green)'; });
    zone.addEventListener('dragleave', () => { zone.style.borderColor=''; });
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.style.borderColor = '';
      if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    });
  }

  window.onFileSelected = function(e) {
    if (e.target.files[0]) handleFile(e.target.files[0]);
  };

  async function handleFile(file) {
    selectedFile = file;

    // Show preview
    const preview    = document.getElementById('upload-preview');
    const previewImg = document.getElementById('preview-img');
    const zone       = document.getElementById('upload-zone');
    const nextBtn    = document.getElementById('step1-next');

    if (previewImg) previewImg.src = URL.createObjectURL(file);
    preview?.classList.remove('hidden');
    zone?.classList.add('hidden');

    // Show loading state
    const inferResult = document.getElementById('infer-result');
    if (inferResult) {
      inferResult.innerHTML = `
        <div class="quick-infer-loading">
          <div class="spinner" style="width:20px;height:20px;border-width:2px"></div>
          <span id="ai-scan-msg">🤖 AI scanning your photo…</span>
        </div>`;
    }
    if (nextBtn) nextBtn.disabled = true;

    // Call quick-infer
    try {
      const fd = new FormData();
      fd.append('image', file, file.name);
      const res  = await fetch('/api/v1/quick-infer', { method: 'POST', body: fd });
      const data = await res.json();

      if (data.status === 'quality_failed') {
        showQualityFail(data.quality);
        if (nextBtn) nextBtn.disabled = false;  // still allow proceeding
        return;
      }

      // Store AI detections
      aiDetected = data.auto_fill || {};

      // Show result card
      const conf    = data.prediction?.confidence || 0;
      const name    = data.prediction?.display_name || '—';
      const confPct = Math.round(conf * 100);

      if (inferResult) {
        const cls = conf >= 0.75 ? 'quality-good' : 'quality-warn';
        inferResult.innerHTML = `
          <div class="quality-card ${cls}">
            <div style="flex:1">
              <div style="font-size:0.95rem;font-weight:800">🤖 ${name}</div>
              <div style="font-size:0.75rem;opacity:0.8">AI confidence: ${confPct}%
                · ${data.provider || 'FIXTURE'}
                ${confPct < 60 ? ' · Low confidence — please confirm manually' : ''}
              </div>
            </div>
            <span class="ai-badge">${confPct}%</span>
          </div>`;
      }

      if (nextBtn) {
        nextBtn.disabled = false;
        const lbl = document.getElementById('step1-next-lbl');
        if (lbl) lbl.textContent = Object.keys(aiDetected).length > 0
          ? '✅ AI detected fields — Confirm →'
          : 'Next — Add Details →';
      }

      // Pre-apply AI selections when user goes to step 2
      sessionStorage.setItem('pp_ai_detect', JSON.stringify(aiDetected));

    } catch (err) {
      if (inferResult) {
        inferResult.innerHTML = `<div class="quality-card quality-warn">⚠️ Could not analyse image — proceeding. (${err.message})</div>`;
      }
      if (nextBtn) nextBtn.disabled = false;
    }
  }

  function showQualityFail(q) {
    const inferResult = document.getElementById('infer-result');
    if (!inferResult) return;
    const msgs = {
      BLURRY:         '📷 Image is too blurry — hold steady and retake.',
      TOO_DARK:       '🌑 Image is too dark — retake in better lighting.',
      TOO_BRIGHT:     '☀️ Image is overexposed — avoid direct sunlight.',
      TOO_SMALL:      '🔍 Image too small — get closer to the plant.',
      INVALID_FORMAT: '❌ File type not supported — use JPG or PNG.',
    };
    inferResult.innerHTML = `<div class="quality-card quality-bad">❌ ${msgs[q.quality_state] || q.message}</div>`;
  }

  window.removeImage = function() {
    selectedFile = null;
    aiDetected   = {};
    const input = document.getElementById('file-input');
    if (input) input.value = '';
    document.getElementById('upload-preview')?.classList.add('hidden');
    document.getElementById('upload-zone')?.classList.remove('hidden');
    const ir = document.getElementById('infer-result');
    if (ir) ir.innerHTML = '';
    const nextBtn = document.getElementById('step1-next');
    if (nextBtn) { nextBtn.disabled = false; }
    const lbl = document.getElementById('step1-next-lbl');
    if (lbl) lbl.textContent = 'Next — Add Details →';
  };

  // ── Apply AI detections when entering step 2 ──────────────
  function applyAIDetections() {
    const stored = sessionStorage.getItem('pp_ai_detect');
    const detected = stored ? JSON.parse(stored) : aiDetected;

    if (!detected || Object.keys(detected).length === 0) return;

    // Build chip display
    showAIBanner(detected);

    // Auto-select in icon grids
    Object.entries(detected).forEach(([field, val]) => {
      autoSelectField(field, val, true /* isAI */);
    });
  }

  // ── AI Banner ─────────────────────────────────────────────
  let _lastDetected = {};
  function showAIBanner(detected) {
    _lastDetected = detected || {};
    const bar  = document.getElementById('ai-detected-bar');
    const row  = document.getElementById('ai-chips-row');
    const conf = document.getElementById('ai-confidence-lbl');
    if (!bar || !row) return;

    if (!_lastDetected || Object.keys(_lastDetected).length === 0) {
      bar.classList.add('hidden'); return;
    }

    const FIELD_LABELS = {
      en: { crop:'Crop', symptom_group:'Symptom', severity:'Severity', growth_stage:'Stage' },
      kn: { crop:'ಬೆಳೆ', symptom_group:'ರೋಗ', severity:'ತೀವ್ರತೆ', growth_stage:'ಹಂತ' },
      hi: { crop:'फसल', symptom_group:'लक्षण', severity:'गंभीरता', growth_stage:'चरण' },
    };
    const fl = FIELD_LABELS[currentLanguage] || FIELD_LABELS.en;

    row.innerHTML = Object.entries(_lastDetected).map(([f, v]) =>
      `<span class="ai-chip">${fl[f] || f}: <strong>${v}</strong></span>`
    ).join('');

    bar.classList.remove('hidden');
  }
  window.renderAIBanner = function() { showAIBanner(_lastDetected); };

  // ── Select icon option (with AI flag) ────────────────────
  function autoSelectField(field, val, isAI = false) {
    const gridMap = {
      crop:          'crop-grid',
      growth_stage:  'stage-grid',
      symptom_group: 'symptom-grid',
    };
    if (field === 'severity') {
      pickSev(null, val);
      form.severity = val;
      return;
    }
    const gridId = gridMap[field];
    if (!gridId) return;
    const grid = document.getElementById(gridId);
    if (!grid) return;

    grid.querySelectorAll('.icon-option').forEach(opt => {
      const match = opt.dataset.val === val;
      opt.classList.toggle('selected', match);
      if (match && isAI) opt.setAttribute('data-ai', '1');
      else opt.removeAttribute('data-ai');
    });
    form[field] = val;
  }
  window.autoSelectField = autoSelectField;

  // ── Icon tap (manual selection) ───────────────────────────
  window.pick = function(field, el) {
    const grid = el.closest('.icon-grid');
    grid?.querySelectorAll('.icon-option').forEach(o => {
      o.classList.remove('selected');
      o.removeAttribute('data-ai');
    });
    el.classList.add('selected');
    form[field] = el.dataset.val;
    // Update AI banner to mark this field as overridden
    if (_lastDetected[field] && _lastDetected[field] !== el.dataset.val) {
      const chip = document.querySelector(`#ai-chips-row .ai-chip`);
      // visually de-emphasize
    }
  };

  // ── Severity selection ────────────────────────────────────
  window.pickSev = function(el, val) {
    document.querySelectorAll('.severity-btn').forEach(b => b.classList.remove('selected'));
    const target = el || document.querySelector(`.severity-btn[data-val="${val}"]`);
    if (target) target.classList.add('selected');
    form.severity = val || (el ? el.dataset.val : null);
  };

  // ── Rain selection ────────────────────────────────────────
  window.pickRain = function(el) {
    document.querySelectorAll('.rain-btn').forEach(b => b.classList.remove('selected'));
    el.classList.add('selected');
    form.recent_rain = el.dataset.val;
  };

  // ── Voice toggle ──────────────────────────────────────────
  window.toggleMic = function() {
    const micBtn    = document.getElementById('mic-btn');
    const micStatus = document.getElementById('mic-status');
    if (micBtn) micBtn.dataset.defaultLabel = '🎤 Speak';
    startVoiceInput(micBtn, micStatus);
  };

  // ── GPS location ──────────────────────────────────────────
  function initGPS() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(pos => {
        form.lat = pos.coords.latitude;
        form.lon = pos.coords.longitude;
      }, () => {});
    }
  }

  // ── Step 3 summary ────────────────────────────────────────
  function buildSummary() {
    const el = document.getElementById('summary-card');
    if (!el) return;
    const CROP_LABELS = window.ICON_LABELS?.[currentLanguage] || {};
    const rows = [
      ['🌾', CROP_LABELS['lbl-crop'] || 'Crop',     form.crop          || '—'],
      ['📅', CROP_LABELS['lbl-stage'] || 'Stage',   form.growth_stage  || '—'],
      ['🔍', CROP_LABELS['lbl-symptom'] || 'Symptom', form.symptom_group || '—'],
      ['⚠️', CROP_LABELS['lbl-severity'] || 'Severity', form.severity    || '—'],
      ['🌧️', CROP_LABELS['lbl-rain'] || 'Rain',     form.recent_rain   || '—'],
      ['📍', 'Location', `${form.lat.toFixed(2)}, ${form.lon.toFixed(2)}`],
      ['📷', 'Image',    selectedFile ? selectedFile.name : 'No image'],
    ];
    el.innerHTML = rows.map(([icon, k, v]) => `
      <div class="summary-row">
        <span style="color:var(--text-muted);font-size:0.85rem">${icon} ${k}</span>
        <span style="font-weight:700;font-size:0.88rem;text-align:right;max-width:60%">${v}</span>
      </div>`).join('');
  }

  // ── Submit ────────────────────────────────────────────────
  window.submitTriage = async function() {
    const btn = document.getElementById('submit-btn');
    const lbl = document.getElementById('submit-lbl');
    if (btn) btn.disabled = true;
    if (lbl) lbl.textContent = '⏳ Submitting…';
    showLoading();

    const fd = new FormData();
    fd.append('crop',           form.crop           || 'unknown');
    fd.append('growth_stage',   form.growth_stage   || 'vegetative');
    fd.append('symptom_group',  form.symptom_group  || 'leaf_spots');
    fd.append('severity',       form.severity       || 'unknown');
    fd.append('recent_rain',    form.recent_rain    || 'unknown');
    fd.append('lat',            form.lat);
    fd.append('lon',            form.lon);
    fd.append('language',       currentLanguage);
    fd.append('client_event_id', crypto.randomUUID ? crypto.randomUUID() : `e-${Date.now()}`);
    if (form.trap_count) fd.append('trap_count', form.trap_count);
    if (selectedFile) fd.append('image', selectedFile, selectedFile.name);

    try {
      const data = await API.post('/api/v1/observations', fd, true /* isForm */);
      hideLoading();
      sessionStorage.removeItem('pp_ai_detect');
      window.location.href = `/result?id=${data.observation_id}`;
    } catch (err) {
      hideLoading();
      if (btn) btn.disabled = false;
      if (lbl) lbl.textContent = 'Submit for Analysis';
      showToast(`❌ ${err.message}`, 'red');
    }
  };

  // ── Trap count ────────────────────────────────────────────
  function initTrap() {
    document.getElementById('trap-count')?.addEventListener('input', e => {
      form.trap_count = parseInt(e.target.value) || null;
    });
  }

  // ── Hook step 2 entry to apply AI detections ──────────────
  const _origGoStep = window.goStep;
  window.goStep = function(n) {
    _origGoStep(n);
    if (n === 2) applyAIDetections();
  };

  // ── Init ──────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initGPS();
    initTrap();
    goStep(1);

    // Apply saved language
    if (typeof setLang === 'function') setLang(currentLanguage);
  });

})();

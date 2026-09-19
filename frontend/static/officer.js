/* ============================================================
   PestPulse — Officer Dashboard JS (officer.html)
   Case queue, stats, side panel, review submission
   ============================================================ */

(function () {
    'use strict';

    let currentCaseId   = null;
    let currentFilter   = 'all';
    let allCases        = [];
    const reviewForm    = { decision: null, note: '', followup_days: 3 };

    // ── Bootstrap ─────────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
        loadStats();
        loadQueue();
        wireFilters();
        wireSidePanel();
        wireReviewButtons();

        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(() => {});
        }
    });

    // ── Stats cards ───────────────────────────────────────────────────────────
    async function loadStats() {
        try {
            const data = await API.get('/api/v1/officer/stats');
            setText('stat-review',   data.needs_review  ?? 0);
            setText('stat-severe',   data.severe_cases  ?? 0);
            setText('stat-followup', data.followup_due  ?? 0);
            setText('stat-total',    data.total_cases   ?? 0);
        } catch {
            // demo fallback
            setText('stat-review', 4); setText('stat-severe', 2);
            setText('stat-followup', 3); setText('stat-total', 18);
        }
    }

    function setText(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    // ── Case queue ────────────────────────────────────────────────────────────
    async function loadQueue(status) {
        const tbody = document.getElementById('queue-body');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--text-muted)">Loading…</td></tr>`;

        try {
            let url = '/api/v1/officer/queue?page_size=50';
            if (status && status !== 'all') url += `&status=${status}`;
            const data = await API.get(url);
            allCases = data.items || [];
        } catch {
            allCases = DEMO_CASES;
        }

        renderQueue(allCases);
    }

    function renderQueue(cases) {
        const tbody = document.getElementById('queue-body');
        if (!tbody) return;

        if (!cases.length) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-muted)">No cases found.</td></tr>`;
            return;
        }

        tbody.innerHTML = cases.map(c => {
            const color  = statusColor(c.status);
            const score  = c.triage_score ? (c.triage_score * 100).toFixed(0) + '%' : '—';
            const age    = timeSince(c.created_at);
            const flag   = c.review_required ? '<span class="badge badge-red" style="padding:2px 8px;font-size:0.65rem">REVIEW</span>' : '';
            return `
            <tr onclick="openCase('${c.id}')">
                <td><code style="font-size:0.75rem;color:var(--text-muted)">${c.id.slice(0,8)}…</code> ${flag}</td>
                <td>${c.crop || '—'}</td>
                <td>${c.district || '—'}</td>
                <td>${c.severity || '—'}</td>
                <td>
                    <span class="status-dot" style="background:var(--${color})"></span>
                    <span style="font-size:0.82rem">${statusLabel(c.status)}</span>
                </td>
                <td>
                    <div style="display:flex;align-items:center;gap:8px">
                        <div class="score-bar-wrap" style="width:60px">
                            <div class="score-bar ${color}" style="width:${(c.triage_score||0)*100}%"></div>
                        </div>
                        <span style="font-size:0.8rem;color:var(--text-muted)">${score}</span>
                    </div>
                </td>
                <td style="font-size:0.78rem;color:var(--text-muted)">${age}</td>
                <td><button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();openCase('${c.id}')">Review →</button></td>
            </tr>`;
        }).join('');
    }

    window.openCase = function(id) {
        currentCaseId = id;
        openSidePanel(id);
    };

    // ── Filters ───────────────────────────────────────────────────────────────
    function wireFilters() {
        document.querySelectorAll('.chip[data-filter]').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('.chip[data-filter]').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                currentFilter = chip.dataset.filter;
                loadQueue(currentFilter === 'all' ? null : currentFilter);
            });
        });
    }

    // ── Side panel ────────────────────────────────────────────────────────────
    function wireSidePanel() {
        document.getElementById('panel-close')?.addEventListener('click', closeSidePanel);
        document.getElementById('panel-overlay')?.addEventListener('click', closeSidePanel);
    }

    function closeSidePanel() {
        document.getElementById('side-panel')?.classList.remove('open');
        document.getElementById('panel-overlay')?.classList.add('hidden');
        currentCaseId = null;
    }

    async function openSidePanel(id) {
        const panel   = document.getElementById('side-panel');
        const overlay = document.getElementById('panel-overlay');
        if (!panel) return;

        panel.classList.add('open');
        overlay?.classList.remove('hidden');

        const body = document.getElementById('panel-body');
        if (body) body.innerHTML = `<div style="display:flex;justify-content:center;padding:40px"><div class="spinner"></div></div>`;

        try {
            const obs = await API.get(`/api/v1/observations/${id}`);
            renderPanel(obs);
        } catch {
            const demo = DEMO_CASES.find(c => c.id === id) || DEMO_CASES[0];
            renderPanelDemo(demo);
        }
    }

    function renderPanel(obs) {
        const o   = obs.observation || {};
        const m   = obs.media       || {};
        const p   = obs.prediction  || {};
        const ev  = obs.evidence_breakdown || {};
        const aud = obs.audit_trail || [];

        const color = statusColor(o.status);
        const topK  = p.top_k_json ? tryParse(p.top_k_json) : [];
        const topPred = topK[0] || {};
        const confPct  = topPred.confidence ? (topPred.confidence * 100).toFixed(0) : '—';

        const body = document.getElementById('panel-body');
        if (!body) return;

        body.innerHTML = `
        <!-- ID & status -->
        <div style="display:flex;justify-content:space-between;align-items:center">
            <code style="color:var(--text-muted);font-size:0.78rem">${o.id?.slice(0,16)}…</code>
            <span class="badge badge-${color}">${statusLabel(o.status)}</span>
        </div>

        <!-- Image -->
        ${m.relative_path ? `
        <div>
            <div class="card-title mb-8">📷 Field Photo</div>
            <img src="/media/${m.relative_path}" style="width:100%;border-radius:10px;max-height:220px;object-fit:cover" onerror="this.style.display='none'">
            <div class="quality-card ${m.quality_state === 'GOOD' ? 'quality-good' : 'quality-warn'} mt-8">
                ${m.quality_state === 'GOOD' ? '✅ Image usable' : `⚠️ ${m.quality_state}`}
                ${m.blur_score ? ` · Blur: ${m.blur_score}` : ''}
            </div>
        </div>` : '<div class="alert alert-amber">⚠️ No image submitted</div>'}

        <!-- AI prediction -->
        ${topPred.display_name ? `
        <div class="card">
            <div class="card-title mb-8">🤖 Model Screening</div>
            <div style="font-size:1rem;font-weight:700">${topPred.display_name}</div>
            <div style="display:flex;align-items:center;gap:10px;margin-top:8px">
                <div class="score-bar-wrap" style="flex:1">
                    <div class="score-bar ${color}" style="width:${confPct}%"></div>
                </div>
                <span class="text-sm fw-700">${confPct}%</span>
            </div>
            <div class="text-xs text-muted mt-8">Provider: ${p.provider || '—'} · Model: ${p.model_version || '—'}</div>
            <div class="alert alert-amber mt-8" style="font-size:0.78rem">Screening signal only — not a definitive diagnosis</div>
        </div>` : ''}

        <!-- Score -->
        <div class="card">
            <div class="card-title mb-8">📊 Triage Score</div>
            <div style="display:flex;align-items:baseline;gap:8px">
                <span class="result-score-big ${color}">${(o.triage_score||0).toFixed(2)}</span>
                <span class="text-muted text-sm">/ 1.00</span>
            </div>
            <div class="score-bar-wrap mt-8">
                <div class="score-bar ${color}" style="width:${(o.triage_score||0)*100}%"></div>
            </div>
        </div>

        <!-- Evidence chips -->
        <div>
            <div class="card-title mb-8">🧩 Evidence Breakdown</div>
            <div class="evidence-grid">
                ${Object.entries(ev).map(([k,v]) => `
                <div class="ev-chip">
                    <div class="ev-label">${k}</div>
                    <div class="ev-score">${((v.score||0)*100).toFixed(0)}%</div>
                    <div class="ev-mini-bar"><div class="ev-fill" style="width:${(v.score||0)*100}%"></div></div>
                </div>`).join('')}
            </div>
        </div>

        <!-- Reasoning -->
        <div class="card">
            <div class="card-title mb-8">💡 Reasoning</div>
            <p style="font-size:0.85rem">${o.reasoning || '—'}</p>
        </div>

        <!-- Field context -->
        <div class="card">
            <div class="card-title mb-8">🌾 Field Context</div>
            ${[['Crop',o.crop],['Stage',o.growth_stage],['Symptom',o.symptom_group],
               ['Severity',o.severity],['Rain',o.recent_rain],['District',o.district]
            ].map(([k,v]) => v ? `
            <div class="market-row">
                <span class="text-muted text-sm">${k}</span>
                <span class="fw-700">${v}</span>
            </div>` : '').join('')}
        </div>

        <!-- Officer action -->
        <div class="card" id="review-panel">
            <div class="card-title mb-8">✅ Officer Action</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
                ${[
                    ['CONFIRM_MONITOR','Confirm Monitor','btn-ghost'],
                    ['LOW_RISK_ACTION','Low-Risk Action','btn-amber'],
                    ['CONFIRM_REVIEW', 'Needs More Info','btn-secondary'],
                    ['REFER',          'Create Referral','btn-danger'],
                    ['RESOLVED',       'Mark Resolved',  'btn-primary'],
                ].map(([dec,lbl,cls]) => `
                <button class="btn ${cls} btn-sm review-action" data-decision="${dec}">${lbl}</button>
                `).join('')}
            </div>
            <textarea id="officer-note" rows="3" class="form-input" placeholder="Officer notes (optional)…" style="resize:vertical"></textarea>
            <div style="display:flex;gap:8px;margin-top:10px;align-items:center">
                <span class="text-xs text-muted">Follow-up:</span>
                ${[3,7,14].map(d => `<button class="chip followup-day" data-days="${d}">${d}d</button>`).join('')}
            </div>
            <button id="submit-review-btn" class="btn btn-primary w-100 mt-16" disabled>Submit Review</button>
        </div>

        <!-- Audit timeline -->
        ${aud.length ? `
        <div>
            <div class="card-title mb-8">🕐 Audit Trail</div>
            <div class="timeline">
                ${aud.map(a => `
                <div class="timeline-item">
                    <div class="timeline-dot green"></div>
                    <div class="timeline-content">
                        <div class="timeline-time">${fmtDate(a.created_at)}</div>
                        <div class="timeline-text fw-700">${a.event_type}</div>
                        <div class="text-xs text-muted">${a.actor_role}</div>
                    </div>
                </div>`).join('')}
            </div>
        </div>` : ''}
        `;

        wireReviewPanel();
    }

    function renderPanelDemo(demo) {
        const body = document.getElementById('panel-body');
        if (!body) return;
        body.innerHTML = `
        <div class="alert alert-amber">⚠️ Demo data — API unavailable</div>
        <div class="card">
            <div class="card-title mb-8">Field Context</div>
            ${[['Crop',demo.crop],['Status',demo.status],['Score',demo.triage_score],['Severity',demo.severity]].map(([k,v])=>`
            <div class="market-row"><span class="text-muted text-sm">${k}</span><span class="fw-700">${v}</span></div>`).join('')}
        </div>
        <div class="card" id="review-panel">
            <div class="card-title mb-8">✅ Officer Action</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
                ${[['CONFIRM_MONITOR','Confirm Monitor','btn-ghost'],['REFER','Create Referral','btn-danger'],['RESOLVED','Mark Resolved','btn-primary']].map(([dec,lbl,cls])=>`
                <button class="btn ${cls} btn-sm review-action" data-decision="${dec}">${lbl}</button>`).join('')}
            </div>
            <textarea id="officer-note" rows="3" class="form-input" placeholder="Notes…"></textarea>
            <button id="submit-review-btn" class="btn btn-primary w-100 mt-16" disabled>Submit Review</button>
        </div>`;
        wireReviewPanel();
    }

    // ── Review panel wiring ───────────────────────────────────────────────────
    function wireReviewButtons() {}   // hooked per-panel open

    function wireReviewPanel() {
        document.querySelectorAll('.review-action').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.review-action').forEach(b => b.style.outline = '');
                btn.style.outline = '2px solid var(--green)';
                reviewForm.decision = btn.dataset.decision;
                const submitBtn = document.getElementById('submit-review-btn');
                if (submitBtn) submitBtn.disabled = false;
            });
        });

        document.querySelectorAll('.followup-day').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('.followup-day').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                reviewForm.followup_days = parseInt(chip.dataset.days);
            });
        });

        document.getElementById('officer-note')?.addEventListener('input', e => {
            reviewForm.note = e.target.value;
        });

        document.getElementById('submit-review-btn')?.addEventListener('click', submitReview);
    }

    async function submitReview() {
        if (!currentCaseId || !reviewForm.decision) return;
        const btn = document.getElementById('submit-review-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'Submitting…'; }

        try {
            const res = await API.patch(`/api/v1/officer/observations/${currentCaseId}/review`, {
                decision:          reviewForm.decision,
                note:              reviewForm.note,
                followup_due_days: reviewForm.followup_days,
                idempotency_key:   `${currentCaseId}-${Date.now()}`,
            });
            showToast('✅ Review submitted', 'green');
            closeSidePanel();
            loadStats();
            loadQueue(currentFilter === 'all' ? null : currentFilter);
        } catch (err) {
            showToast(`❌ ${err.message}`, 'red');
            if (btn) { btn.disabled = false; btn.textContent = 'Submit Review'; }
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    function timeSince(isoStr) {
        if (!isoStr) return '—';
        const diff = Date.now() - new Date(isoStr).getTime();
        const m = Math.floor(diff / 60000);
        if (m < 60)    return `${m}m ago`;
        const h = Math.floor(m / 60);
        if (h < 24)    return `${h}h ago`;
        return `${Math.floor(h/24)}d ago`;
    }

    function fmtDate(isoStr) {
        if (!isoStr) return '—';
        return new Date(isoStr).toLocaleString();
    }

    function tryParse(str) {
        try { return JSON.parse(str); } catch { return []; }
    }

    // ── Demo fixture cases ────────────────────────────────────────────────────
    const DEMO_CASES = [
        { id:'demo-001', crop:'Tomato',    district:'Bengaluru', severity:'many',    status:'review_required', triage_score:0.73, review_required:1, created_at: new Date(Date.now()-3600000).toISOString() },
        { id:'demo-002', crop:'Potato',    district:'Tumkur',    severity:'few',     status:'monitor',         triage_score:0.41, review_required:0, created_at: new Date(Date.now()-7200000).toISOString() },
        { id:'demo-003', crop:'Corn',      district:'Kolar',     severity:'almost_all', status:'review_required', triage_score:0.85, review_required:1, created_at: new Date(Date.now()-1800000).toISOString() },
        { id:'demo-004', crop:'Grape',     district:'Chikkaballapur', severity:'few', status:'low_risk_action', triage_score:0.55, review_required:0, created_at: new Date(Date.now()-86400000).toISOString() },
        { id:'demo-005', crop:'Pepper',    district:'Ramanagara', severity:'many',   status:'resolved',        triage_score:0.62, review_required:0, created_at: new Date(Date.now()-172800000).toISOString() },
    ];

})();

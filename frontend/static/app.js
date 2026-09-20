/* ============================================================
   PestPulse — Shared App JS v2
   Language system, Voice (Bhashini → Web Speech fallback),
   API helpers, Toast, Loading overlay, Particles
   ============================================================ */

// ─────────────────────────────────────────────────────────────
// 1. LANGUAGE SYSTEM
// ─────────────────────────────────────────────────────────────
let currentLanguage = localStorage.getItem('pp_lang') || 'en';

// Called from every page's inline setLang override, or directly
function setLanguage(lang) {
  currentLanguage = lang;
  localStorage.setItem('pp_lang', lang);

  // Fix active state — ONLY mark the button whose data-lang matches
  document.querySelectorAll('.lang-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.lang === lang);
  });

  // data-i18n text replacement
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const v = _i18n(el.dataset.i18n);
    if (v) el.textContent = v;
  });

  // data-i18n-ph placeholder replacement
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const v = _i18n(el.dataset.i18nPh);
    if (v) el.placeholder = v;
  });
}

// Shorthand strings used across pages
const _STRINGS = {
  en: {
    loading: 'Analysing…',
    mic_listening: '🎙 Listening… say crop, symptom, severity',
    mic_blocked: '⚠️ Mic blocked. Allow access in Chrome (padlock icon).',
    mic_nosupport: '⚠️ Voice not supported. Use Chrome or Edge.',
    mic_error: '⚠️ Voice error — try again.',
    mic_nomatch: '⚠️ Not understood. Try: "tomato, leaf spots, many"',
    mic_filled: '✅ Filled {n} field(s) from voice',
    caution: 'AI screening signal only — not a confirmed diagnosis.',
  },
  kn: {
    loading: 'ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ…',
    mic_listening: '🎙 ಆಲಿಸುತ್ತಿದ್ದೇನೆ… ಬೆಳೆ, ರೋಗ, ತೀವ್ರತೆ ಹೇಳಿ',
    mic_blocked: '⚠️ ಮೈಕ್ ಅನುಮತಿ ನೀಡಿ (Chrome ಲಾಕ್ ಐಕಾನ್).',
    mic_nosupport: '⚠️ ವಾಯ್ಸ್ ಬೆಂಬಲಿತವಲ್ಲ. Chrome ಬಳಸಿ.',
    mic_error: '⚠️ ದೋಷ ಆಗಿದೆ — ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',
    mic_nomatch: '⚠️ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಪ್ರಯತ್ನಿಸಿ: "ಟೊಮೇಟೊ, ಕಲೆ, ಹೆಚ್ಚು"',
    mic_filled: '✅ {n} ಕ್ಷೇತ್ರ ತುಂಬಲಾಗಿದೆ',
    caution: 'ಇದು AI ತಪಾಸಣಾ ಸಂಕೇತ, ನಿರ್ಣಾಯಕ ರೋಗ ನಿರ್ಣಯ ಅಲ್ಲ.',
  },
  hi: {
    loading: 'विश्लेषण हो रहा है…',
    mic_listening: '🎙 सुन रहा हूँ… फसल, लक्षण, गंभीरता बताएं',
    mic_blocked: '⚠️ माइक की अनुमति दें (Chrome लॉक आइकन).',
    mic_nosupport: '⚠️ वॉयस समर्थित नहीं। Chrome उपयोग करें।',
    mic_error: '⚠️ त्रुटि — फिर प्रयास करें।',
    mic_nomatch: '⚠️ समझ नहीं आया। प्रयास करें: "टमाटर, धब्बे, बहुत"',
    mic_filled: '✅ {n} फ़ील्ड भरे',
    caution: 'यह AI जाँच संकेत है, पक्का निदान नहीं।',
  },
};
function _i18n(key) {
  const dict = _STRINGS[currentLanguage] || _STRINGS.en;
  return dict[key] || (_STRINGS.en[key] || '');
}
function t(key) { return _i18n(key); }

// Wire up lang switcher buttons on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  // Make sure each lang-btn has data-lang (set from onclick attribute)
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const lang = btn.dataset.lang;
      if (lang) {
        if (typeof setLang === 'function') setLang(lang);
        else setLanguage(lang);
      }
    });
  });
  setLanguage(currentLanguage);
  initParticles(document.querySelector('.particles'));
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
});

// ─────────────────────────────────────────────────────────────
// 2. API HELPERS
// ─────────────────────────────────────────────────────────────
const API = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  async post(path, body, isForm = false) {
    const opts = { method: 'POST', body };
    if (!isForm) opts.headers = { 'Content-Type': 'application/json' };
    const r = await fetch(path, opts);
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || r.statusText);
    }
    return r.json();
  },
  async patch(path, body) {
    const r = await fetch(path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  },
};

// ─────────────────────────────────────────────────────────────
// 3. TOAST & LOADING
// ─────────────────────────────────────────────────────────────
function showToast(msg, type = 'green', ms = 3500) {
  let el = document.getElementById('pp-toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'pp-toast';
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.className = `toast ${type} show`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), ms);
}

function showLoading(msg) {
  const el = document.getElementById('loading-overlay');
  if (!el) return;
  const m = document.getElementById('loading-msg');
  if (m) m.textContent = msg || t('loading');
  el.classList.add('show');
}
function hideLoading() {
  document.getElementById('loading-overlay')?.classList.remove('show');
}

// ─────────────────────────────────────────────────────────────
// 4. STATUS COLOUR / LABEL
// ─────────────────────────────────────────────────────────────
function statusColor(status) {
  return { monitor:'green', low_risk_action:'amber', review_required:'red',
           resolved:'green', invalid_input:'grey', source_unavailable:'grey' }[status] || 'grey';
}
function statusLabel(status, lang) {
  const l = lang || currentLanguage;
  const m = {
    monitor:           { en:'Monitor',          kn:'ಗಮನಿಸಿ',           hi:'निगरानी' },
    low_risk_action:   { en:'Low-Risk Action',  kn:'ಕಡಿಮೆ ಅಪಾಯ ಕ್ರಮ', hi:'कम जोखिम' },
    review_required:   { en:'Expert Review',    kn:'ತಜ್ಞ ಪರಿಶೀಲನೆ',    hi:'विशेषज्ञ समीक्षा' },
    resolved:          { en:'Resolved',         kn:'ಪರಿಹರಿಸಲಾಗಿದೆ',   hi:'हल हुआ' },
    invalid_input:     { en:'Invalid Input',    kn:'ಅಮಾನ್ಯ',           hi:'अमान्य' },
    source_unavailable:{ en:'Data Unavailable', kn:'ಲಭ್ಯವಿಲ್ಲ',        hi:'उपलब्ध नहीं' },
  };
  return (m[status] || {})[l] || (m[status] || {}).en || status;
}

// ─────────────────────────────────────────────────────────────
// 5. PARTICLES (hero background)
// ─────────────────────────────────────────────────────────────
function initParticles(container) {
  if (!container) return;
  for (let i = 0; i < 18; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const sz = Math.random() * 6 + 3;
    p.style.cssText = `width:${sz}px;height:${sz}px;left:${Math.random()*100}%;
      animation-duration:${Math.random()*15+10}s;animation-delay:${Math.random()*12}s;`;
    container.appendChild(p);
  }
}

// ─────────────────────────────────────────────────────────────
// 6. VOICE ENGINE  (Bhashini primary → Web Speech fallback)
// ─────────────────────────────────────────────────────────────

// 6a. TTS — speak result text
let _voices = [];
if (window.speechSynthesis) {
  const _loadV = () => { _voices = speechSynthesis.getVoices(); };
  speechSynthesis.onvoiceschanged = _loadV;
  setTimeout(_loadV, 400);
  setTimeout(_loadV, 1500);
}

async function speakText(text, lang) {
  if (!text) return;
  const l = lang || currentLanguage;

  // Try backend TTS (gTTS or Bhashini depending on server config)
  // gTTS handles Kannada and Hindi well — no API key required
  try {
    const res = await fetch('/api/v1/voice/tts', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ text, lang: l }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.audio_b64) {
        const bytes = atob(data.audio_b64);
        const arr   = new Uint8Array(bytes.length);
        for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
        // gTTS returns mp3, Bhashini returns wav — both work with Audio()
        const mime  = data.format === 'wav' ? 'audio/wav' : 'audio/mpeg';
        const blob  = new Blob([arr], { type: mime });
        const url   = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.play();
        audio.onended = () => URL.revokeObjectURL(url);
        return;
      }
    }
  } catch (_) {}

  // Final fallback: browser Web Speech API (English only works reliably)
  _webSpeakText(text, l);
}

function _webSpeakText(text, lang) {
  if (!window.speechSynthesis) return;
  speechSynthesis.cancel();
  const codes = { en:'en-IN', kn:'kn-IN', hi:'hi-IN' };
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate  = 0.9; utter.pitch = 1.0;
  const code  = codes[lang || currentLanguage] || 'en-IN';
  let v = _voices.find(v => v.lang === code)
       || _voices.find(v => v.lang.startsWith(code.split('-')[0]))
       || _voices.find(v => v.lang.startsWith('en'));
  if (v) { utter.voice = v; utter.lang = v.lang; }
  else utter.lang = code;
  speechSynthesis.speak(utter);
}

function stopSpeaking() { window.speechSynthesis?.cancel(); }

// 6b. ASR — mic → transcript → form fill
let _bhashiniStatus = null;
async function _getBhashiniStatus() {
  if (_bhashiniStatus) return _bhashiniStatus;
  try {
    _bhashiniStatus = await API.get('/api/v1/voice/status');
  } catch {
    _bhashiniStatus = { bhashini_enabled: false };
  }
  return _bhashiniStatus;
}

let _recorder    = null;
let _audioChunks = [];
let _recActive   = false;

async function startVoiceInput(micBtnEl, micStatusEl) {
  if (_recActive) { _stopRecording(micBtnEl, micStatusEl); return; }

  const status = await _getBhashiniStatus();

  if (status.bhashini_enabled) {
    await _startBhashiniASR(micBtnEl, micStatusEl);
  } else {
    _startWebSpeechASR(micBtnEl, micStatusEl);
  }
}

// ── Bhashini ASR (MediaRecorder → POST /api/v1/voice/asr) ──
async function _startBhashiniASR(micBtnEl, micStatusEl) {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    _recorder    = new MediaRecorder(stream);
    _audioChunks = [];
    _recActive   = true;

    _recorder.ondataavailable = e => _audioChunks.push(e.data);
    _recorder.onstop = async () => {
      _recActive = false;
      _setMicUI(micBtnEl, micStatusEl, false, '🔄 Processing…');

      const blob = new Blob(_audioChunks, { type: 'audio/wav' });
      const fd   = new FormData();
      fd.append('audio', blob, 'voice.wav');
      fd.append('lang',  currentLanguage);

      try {
        const res = await fetch('/api/v1/voice/asr', { method: 'POST', body: fd });
        const data = await res.json();
        const transcript = data.transcript || '';
        if (transcript) {
          _processTranscript(transcript, micStatusEl);
        } else {
          if (micStatusEl) micStatusEl.textContent = t('mic_nomatch');
        }
      } catch (e) {
        if (micStatusEl) micStatusEl.textContent = `⚠️ Bhashini error: ${e.message}`;
      }
      stream.getTracks().forEach(t => t.stop());
    };

    _recorder.start();
    _setMicUI(micBtnEl, micStatusEl, true, t('mic_listening'));

    // Auto-stop after 5 seconds
    setTimeout(() => { if (_recActive) _recorder.stop(); }, 5000);

  } catch (err) {
    _recActive = false;
    const msg = err.name === 'NotAllowedError' ? t('mic_blocked') : `⚠️ ${err.message}`;
    if (micStatusEl) { micStatusEl.textContent = msg; micStatusEl.style.display = 'block'; }
  }
}

function _stopRecording(micBtnEl, micStatusEl) {
  _manualStop = true;
  _recActive  = false;
  if (_recorder && _recorder.state !== 'inactive') {
    _recorder.stop();
  }
  if (_voiceRecog) {
    try { _voiceRecog.stop(); } catch(_) {}
  }
  _setMicUI(micBtnEl, micStatusEl, false, '');
}

// ── Web Speech ASR fallback ──
let _voiceRecog = null;
let _manualStop = false;

const LANG_CODES = { en: 'en-IN', kn: 'kn-IN', hi: 'hi-IN' };
let _voiceLangCode = LANG_CODES[currentLanguage] || 'en-IN';

// Called by setLang() to update the active recognition language
function _updateVoiceLang(lang) {
  _voiceLangCode = LANG_CODES[lang] || 'en-IN';
  // If recognition is running, stop and restart won't happen automatically
  // — user must tap mic again after language switch
}

function _startWebSpeechASR(micBtnEl, micStatusEl) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    if (micStatusEl) { micStatusEl.textContent = t('mic_nosupport'); micStatusEl.style.display = 'block'; }
    return;
  }

  _manualStop = false;

  function _createAndStart() {
    _voiceRecog = new SR();
    _voiceRecog.lang            = _voiceLangCode;   // ✅ uses current language
    _voiceRecog.continuous      = true;
    _voiceRecog.interimResults  = true;
    _voiceRecog.maxAlternatives = 5;

    let finalTx = '';

    _voiceRecog.onresult = e => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const chunk = e.results[i][0].transcript;
        if (e.results[i].isFinal) {
          finalTx += ' ' + chunk;
          _processTranscript(finalTx.trim(), null);
        } else {
          interim = chunk;
        }
      }
      if (micStatusEl) {
        micStatusEl.style.display = 'block';
        micStatusEl.textContent = `🎙 "${(finalTx + ' ' + interim).trim()}"`;
      }
    };

    _voiceRecog.onend = () => {
      if (!_manualStop && _recActive) {
        try { _voiceRecog.start(); } catch(_) {}
      } else {
        _recActive = false;
        _setMicUI(micBtnEl, micStatusEl, false, '');
      }
    };

    _voiceRecog.onerror = e => {
      if (e.error === 'no-speech') {
        if (!_manualStop && _recActive) {
          try { _voiceRecog.start(); } catch(_) {}
        }
        return;
      }
      if (e.error === 'not-allowed') {
        _recActive = false; _manualStop = true;
        _setMicUI(micBtnEl, micStatusEl, false, '');
        if (micStatusEl) { micStatusEl.textContent = t('mic_blocked'); micStatusEl.style.display = 'block'; }
        return;
      }
      if (!_manualStop && _recActive) {
        setTimeout(() => { try { _voiceRecog.start(); } catch(_) {} }, 300);
      }
    };

    try { _voiceRecog.start(); }
    catch (e) {
      _recActive = false;
      if (micStatusEl) { micStatusEl.textContent = `⚠️ ${e.message}`; micStatusEl.style.display = 'block'; }
    }
  }

  _recActive = true;
  _setMicUI(micBtnEl, micStatusEl, true, t('mic_listening'));
  _createAndStart();
}

function _setMicUI(micBtnEl, micStatusEl, active, statusText) {
  if (micBtnEl) {
    micBtnEl.classList.toggle('active', active);
    const lbl = micBtnEl.querySelector('[data-mic-lbl]') || micBtnEl;
    lbl.textContent = active ? '🔴 Stop' : (micBtnEl.dataset.defaultLabel || '🎤 Speak');
  }
  if (micStatusEl) {
    micStatusEl.style.display = statusText ? 'block' : 'none';
    micStatusEl.textContent   = statusText;
  }
}

// ── Keyword matcher (works for EN + KN transliterated + HI) ──
const VOICE_VOCAB = {
  crop: {
    tomato:      ['tomato','tamaatar','टमाटर','ಟೊಮೇಟೊ'],
    potato:      ['potato','aloo','aaloo','आलू','ಆಲೂ'],
    corn_maize:  ['maize','corn','makka','makkajola','मक्का','ಮೆಕ್ಕೆ'],
    grape:       ['grape','drakshi','angoor','अंगूर','ದ್ರಾಕ್ಷಿ'],
    bell_pepper: ['pepper','capsicum','shimla','शिमला','ಕ್ಯಾಪ್ಸಿಕಂ'],
    strawberry:  ['strawberry','स्ट्रॉबेरी'],
    orange:      ['orange','narangi','kittale','संतरा','ಕಿತ್ತಳೆ'],
    soybean:     ['soy','soybean','सोयाबीन','ಸೋಯಾ'],
    apple:       ['apple','seb','सेब','ಸೇಬು'],
  },
  symptom_group: {
    leaf_spots:       ['spot','spots','blight','lesion','rust','kale','dhabbhe','धब्बे','ಕಲೆ'],
    yellowing:        ['yellow','yellowing','peela','haldi','पीला','ಹಳದಿ'],
    wilting:          ['wilt','wilting','murjha','baadu','मुरझाना','ಬಾಡು'],
    leaf_curling:     ['curl','curling','twisted','murna','ಸುರುಳಿ','मुड़ना'],
    holes_or_chewing: ['hole','holes','chewed','eaten','insect','chheda','छेद','ರಂಧ್ರ'],
    powder_coating:   ['powder','powdery','mildew','white','safed','सफेद','ಹಿಟ್ಟು'],
    none_visible:     ['healthy','fine','normal','swasth','ठीक','ಆರೋಗ್ಯ'],
  },
  severity: {
    almost_all: ['almost all','everywhere','severe','all','poora','ella','सब','ಎಲ್ಲಾ'],
    many:       ['many','lots','half','bahut','hechu','बहुत','ಹೆಚ್ಚು'],
    few:        ['few','some','little','kuch','kelavu','कुछ','ಕೆಲವು'],
    unknown:    ['unknown','not sure','pata nahi','ಗೊತ್ತಿಲ್ಲ','पता नहीं'],
  },
  growth_stage: {
    seedling:   ['seedling','sprout','molake','ankur','अंकुर','ಮೊಳಕೆ'],
    vegetative: ['vegetative','growing','leaves','patte','पत्ते','ಸಸ್ಯ'],
    flowering:  ['flowering','flower','bloom','huvu','phool','फूल','ಹೂ'],
    fruiting:   ['fruiting','fruit','phal','hannu','फल','ಕಾಯಿ'],
    maturity:   ['mature','harvest','ripe','ready','paka','কাটাई','ಮಾಗಿ'],
  },
  recent_rain: {
    yes: ['rain','rained','baarish','barish','male','बारिश','ಮಳೆ'],
    no:  ['no rain','dry','sunny','sukha','शुष्क','ಒಣ'],
  },
};

function _processTranscript(transcript, micStatusEl) {
  const tx = transcript.toLowerCase();
  const matched = {};

  Object.entries(VOICE_VOCAB).forEach(([field, vals]) => {
    Object.entries(vals).forEach(([val, kws]) => {
      if (kws.some(k => tx.includes(k.toLowerCase()))) {
        matched[field] = val;
      }
    });
  });

  let count = 0;
  Object.entries(matched).forEach(([field, val]) => {
    // Try the page's autoSelect function first (farmer.js), then fallback
    if (typeof autoSelectField === 'function') {
      autoSelectField(field, val);
      count++;
    }
  });

  // ✅ Call the farmer.html voice hook to store transcript in textarea + form
  if (typeof window._voiceOnFinal === 'function') {
    window._voiceOnFinal(transcript);
  }

  if (micStatusEl) {
    micStatusEl.style.display = 'block';
    micStatusEl.textContent = count > 0
      ? t('mic_filled').replace('{n}', count)
      : t('mic_nomatch');
  }
}

// ── Public speak wrapper used by result page ──
function speakResult(result) {
  if (!result) return;
  const statusL = statusLabel(result.status);
  const action  = result.human_action || '';
  // Always speak in English if Bhashini unavailable
  const text = `${statusL}. ${action}`;
  speakText(text, currentLanguage);
}

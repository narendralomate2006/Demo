// ── CONFIG ─────────────────────────────────────────────────
// Auto-detect: use localhost in development, Render URL in production
const IS_LOCAL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:';
const API_BASE_URL = IS_LOCAL
    ? 'http://127.0.0.1:8000'
    : 'https://railway-crowd-monitor.onrender.com';  // ← UPDATE this after deploying on Render


// ── CHARTS ─────────────────────────────────────────────────
let hourlyTrendChart = null;
let busyStationsChart = null;

// Mode icon map
const MODE_ICONS = {
    'Metro':           'fa-solid fa-train-subway text-indigo-400',
    'Metro + Auto':    'fa-solid fa-train-subway text-indigo-400',
    'Bus (PMPML)':     'fa-solid fa-bus text-amber-400',
    'Auto Rickshaw':   'fa-solid fa-motorcycle text-emerald-400',
    'Cab / Auto':      'fa-solid fa-car text-sky-400',
};
function getModeIcon(mode) {
    for (const [key, cls] of Object.entries(MODE_ICONS)) {
        if (mode.startsWith(key)) return cls;
    }
    return 'fa-solid fa-route text-slate-400';
}

// ── INIT ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initTimeSlots();
    fetchStations();
    fetchStats();

    document.getElementById('crowdForm').addEventListener('submit', handleSubmit);
    document.getElementById('btnRefreshStats').addEventListener('click', () => {
        fetchStats();
        showToast('Syncing data from AI engine…');
    });
});

function initTimeSlots() {
    const sel = document.getElementById('timeSlot');
    for (let h = 0; h < 24; h++) {
        const v = String(h).padStart(2, '0') + ':00';
        const opt = document.createElement('option');
        opt.value = v; opt.textContent = v;
        if (h === 8) opt.selected = true;
        sel.appendChild(opt);
    }
}

// ── STATIONS ────────────────────────────────────────────────
async function fetchStations() {
    try {
        const res = await fetch(`${API_BASE_URL}/stations`);
        if (!res.ok) throw new Error('Failed to fetch stations');
        const stations = await res.json();

        const srcSel  = document.getElementById('source');
        const destSel = document.getElementById('destination');
        srcSel.innerHTML  = '<option value="" disabled selected>Select Source</option>';
        destSel.innerHTML = '<option value="" disabled selected>Select Destination</option>';

        stations.forEach((s, i) => {
            const o1 = new Option(s, s); if (i === 0) o1.selected = true; srcSel.appendChild(o1);
            const o2 = new Option(s, s); if (i === 1) o2.selected = true; destSel.appendChild(o2);
        });
    } catch (err) {
        showFormError('Cannot reach the backend server. Please ensure it is running.');
    }
}

// ── PREDICTION ──────────────────────────────────────────────
async function handleSubmit(e) {
    e.preventDefault();
    hideFormError();

    const source      = document.getElementById('source').value;
    const destination = document.getElementById('destination').value;
    const day_of_week = document.getElementById('dayOfWeek').value;
    const time_slot   = document.getElementById('timeSlot').value;

    if (!source || !destination)       { showFormError('Please select both Source and Destination.'); return; }
    if (source === destination)        { showFormError('Source and Destination cannot be the same.'); return; }

    // UI: loading state
    setResultState('loading');

    try {
        await new Promise(r => setTimeout(r, 600)); // small delay for animation feel
        const res = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, destination, day_of_week, time_slot })
        });
        if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'Prediction failed.'); }
        const data = await res.json();
        renderResult(data);
        renderAlternatives(data.alternative_options, data.predicted_crowd_level, data.source, data.destination);
    } catch (err) {
        showFormError(err.message || 'Error contacting the prediction engine.');
        setResultState('placeholder');
    }
}

// ── RENDER RESULT ───────────────────────────────────────────
function renderResult(result) {
    setResultState('content');

    const level = result.predicted_crowd_level;
    const isWeekend = result.is_weekend;

    document.getElementById('predictedLevel').textContent = level;
    document.getElementById('routeSummary').textContent = `${result.source} → ${result.destination}`;
    document.getElementById('resultWeekendBadge').classList.toggle('hidden', !isWeekend);

    // Glow & icon
    const card     = document.getElementById('resultCard');
    const glowDiv  = document.getElementById('crowdIndicatorGlow');
    const iconEl   = document.getElementById('crowdIndicatorIcon');
    const descEl   = document.getElementById('crowdLevelDesc');

    card.classList.remove('glow-green','glow-amber','glow-red');
    glowDiv.className = 'w-16 h-16 rounded-2xl flex items-center justify-center border text-2xl transition-all duration-300';
    iconEl.className  = 'fa-solid';

    switch (level) {
        case 'High':
            card.classList.add('glow-red');
            glowDiv.classList.add('bg-rose-500/10','text-rose-400','border-rose-500/30');
            iconEl.classList.add('fa-triangle-exclamation');
            descEl.textContent = 'High congestion alert! Expect packed coaches and long waiting times. Consider an alternative transport option below.';
            break;
        case 'Medium':
            card.classList.add('glow-amber');
            glowDiv.classList.add('bg-amber-500/10','text-amber-400','border-amber-500/30');
            iconEl.classList.add('fa-people-group');
            descEl.textContent = 'Moderate passenger traffic. Limited seating available. Mild waiting times expected.';
            break;
        default: // Low
            card.classList.add('glow-green');
            glowDiv.classList.add('bg-emerald-500/10','text-emerald-400','border-emerald-500/30');
            iconEl.classList.add('fa-shield-halved');
            descEl.textContent = 'Low crowd density. Comfortable boarding and ample seating. Great time to travel!';
    }
}

// ── RENDER ALTERNATIVES ─────────────────────────────────────
function renderAlternatives(options, crowdLevel, source, destination) {
    const panel   = document.getElementById('altPanel');
    const list    = document.getElementById('altList');
    const crowdTag = document.getElementById('altCrowdTag');

    if (!options || options.length === 0) { panel.classList.add('hidden'); return; }

    // Tag colour
    const tagMap = { High:'bg-rose-500/10 text-rose-400 border-rose-500/20', Medium:'bg-amber-500/10 text-amber-400 border-amber-500/20', Low:'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' };
    crowdTag.className = `text-[10px] font-bold px-2 py-0.5 rounded-full border ${tagMap[crowdLevel] || tagMap.Low}`;
    crowdTag.textContent = `Train: ${crowdLevel} Crowd`;

    list.innerHTML = '';
    options.forEach((opt, idx) => {
        const isBest = idx === 0;
        const iconCls = getModeIcon(opt.mode);

        list.innerHTML += `
        <div class="alt-card bg-slate-900/70 border ${isBest ? 'border-indigo-500/30' : 'border-slate-800/80'} rounded-2xl p-4 flex items-start gap-4 relative">
            ${isBest ? '<span class="absolute top-3 right-3 text-[9px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-400 border border-indigo-500/20 tracking-widest">Best Pick</span>' : ''}
            <!-- Mode icon -->
            <div class="shrink-0 w-10 h-10 rounded-xl flex items-center justify-center border ${isBest ? 'bg-indigo-500/10 border-indigo-500/20' : 'bg-slate-800/80 border-slate-700/50'}">
                <i class="${iconCls} text-base"></i>
            </div>
            <!-- Details -->
            <div class="flex-grow min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-sm font-bold text-white">${opt.mode}</span>
                </div>
                <p class="text-xs text-slate-400 mt-0.5 truncate" title="${opt.route}">${opt.route}</p>
                <p class="text-[10px] text-indigo-300/80 mt-1">${opt.status}</p>
                <!-- Stats row -->
                <div class="flex items-center gap-4 mt-2.5 flex-wrap">
                    <div class="flex items-center gap-1 text-xs text-slate-300">
                        <i class="fa-solid fa-clock text-slate-500 text-[10px]"></i>
                        <span>${opt.duration_mins} mins</span>
                    </div>
                    <div class="flex items-center gap-1 text-xs text-emerald-400">
                        <i class="fa-solid fa-indian-rupee-sign text-[10px]"></i>
                        <span>₹${opt.estimated_fare_inr}</span>
                    </div>
                    <div class="flex items-center gap-1 text-xs text-slate-400">
                        <i class="fa-solid fa-rotate text-slate-500 text-[10px]"></i>
                        <span>${opt.frequency}</span>
                    </div>
                </div>
            </div>
        </div>`;
    });

    panel.classList.remove('hidden');
}

// ── RESULT UI STATE ─────────────────────────────────────────
function setResultState(state) {
    ['resultPlaceholder','resultLoading','resultContent'].forEach(id =>
        document.getElementById(id).classList.add('hidden'));
    if (state === 'placeholder') document.getElementById('resultPlaceholder').classList.remove('hidden');
    if (state === 'loading')     document.getElementById('resultLoading').classList.remove('hidden');
    if (state === 'content')     document.getElementById('resultContent').classList.remove('hidden');
}

// ── STATS & CHARTS ──────────────────────────────────────────
async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE_URL}/historical-stats`);
        if (!res.ok) throw new Error('Stats fetch failed');
        const stats = await res.json();

        document.getElementById('statLowCount').textContent    = stats.crowd_distribution['Low']    || 0;
        document.getElementById('statMediumCount').textContent = stats.crowd_distribution['Medium'] || 0;
        document.getElementById('statHighCount').textContent   = stats.crowd_distribution['High']   || 0;
        document.getElementById('valWeekdayAvg').textContent   = stats.weekend_vs_weekday.weekday_avg.toFixed(2);
        document.getElementById('valWeekendAvg').textContent   = stats.weekend_vs_weekday.weekend_avg.toFixed(2);

        renderHourlyChart(stats.hourly_stats);
        renderStationsChart(stats.busy_stations);
    } catch (err) {
        showFormError('Could not load analytics. Is the backend running?');
    }
}

function renderHourlyChart(hourlyData) {
    const ctx = document.getElementById('hourlyTrendChart');
    if (!ctx) return;
    const labels = Array.from({length:24},(_,i) => String(i).padStart(2,'0')+':00');
    const data   = labels.map((_,i) => hourlyData[i] ?? 1);
    if (hourlyTrendChart) hourlyTrendChart.destroy();
    hourlyTrendChart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets: [{ label:'Crowd Load', data, borderColor:'#6366f1', backgroundColor:'rgba(99,102,241,0.13)', borderWidth:3, fill:true, tension:0.4, pointBackgroundColor:'#4f46e5', pointHoverRadius:6 }] },
        options: {
            responsive:true, maintainAspectRatio:false,
            plugins:{ legend:{display:false} },
            scales:{
                y:{ min:1, max:3, ticks:{ stepSize:1, color:'#94a3b8', callback:v=>({1:'Low',2:'Med',3:'High'}[v]||'') }, grid:{color:'rgba(35,50,74,0.5)'} },
                x:{ ticks:{maxTicksLimit:8,color:'#94a3b8'}, grid:{display:false} }
            }
        }
    });
}

function renderStationsChart(busyStations) {
    const ctx = document.getElementById('busyStationsChart');
    if (!ctx) return;
    const sorted = Object.entries(busyStations).sort((a,b)=>b[1]-a[1]);
    if (busyStationsChart) busyStationsChart.destroy();
    busyStationsChart = new Chart(ctx, {
        type: 'bar',
        data: { labels:sorted.map(x=>x[0]), datasets:[{ label:'High Crowd Count', data:sorted.map(x=>x[1]), backgroundColor:'rgba(244,63,94,0.65)', borderColor:'#f43f5e', borderWidth:1.5, borderRadius:6, barThickness:16 }] },
        options: {
            indexAxis:'y', responsive:true, maintainAspectRatio:false,
            plugins:{ legend:{display:false} },
            scales:{
                x:{ ticks:{color:'#94a3b8',precision:0}, grid:{color:'rgba(35,50,74,0.5)'} },
                y:{ ticks:{color:'#94a3b8'}, grid:{display:false} }
            }
        }
    });
}

// ── ERROR/TOAST HELPERS ─────────────────────────────────────
function showFormError(msg) {
    const el = document.getElementById('formError');
    document.getElementById('errorText').textContent = msg;
    el.classList.remove('hidden');
}
function hideFormError() { document.getElementById('formError').classList.add('hidden'); }

function showToast(message) {
    const t = document.createElement('div');
    t.className = 'fixed bottom-5 right-5 px-5 py-3 rounded-2xl shadow-xl text-xs font-semibold z-50 border bg-slate-900 text-indigo-400 border-indigo-500/20 flex items-center gap-2 transition-all duration-300 translate-y-10 opacity-0';
    t.innerHTML = `<i class="fa-solid fa-circle-info animate-bounce"></i> ${message}`;
    document.body.appendChild(t);
    requestAnimationFrame(() => { t.classList.remove('translate-y-10','opacity-0'); });
    setTimeout(() => { t.classList.add('translate-y-10','opacity-0'); setTimeout(()=>t.remove(),300); }, 3000);
}

// --- CONFIG ---
const API_BASE = "http://127.0.0.1:8000";
const STAGE_ORDER = ["intent", "decomposition", "claims", "critique", "revision", "evaluation"];
const STAGE_LABELS = {
    intent: "Intent Parsing",
    decomposition: "Problem Decomposition",
    claims: "Claim Generation",
    critique: "Adversarial Critique",
    revision: "Epistemic Revision",
    evaluation: "Final Evaluation"
};

// --- STATE ---
let state = {
    runId: null,
    data: null, // Full RunState object
    isPolling: false
};

// --- DOM ELEMENTS ---
const els = {
    setupPanel: document.getElementById('setup-panel'),
    pipelineContainer: document.getElementById('pipeline-container'),
    directiveInput: document.getElementById('directive-input'),
    btnStart: document.getElementById('btn-start'),
    viewerContent: document.getElementById('viewer-content'),
    viewerTitle: document.getElementById('viewer-title'),
    statusBar: document.getElementById('status-bar'),
    toggleProv: document.getElementById('toggle-provenance')
};

// --- API CLIENT ---
async function apiCall(endpoint, method = "GET", body = null) {
    const options = {
        method,
        headers: { "Content-Type": "application/json" }
    };
    if (body) options.body = JSON.stringify(body);

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, options);
        if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
        return await res.json();
    } catch (err) {
        showError(err.message);
        throw err;
    }
}

// --- ACTIONS ---

async function createRun() {
    const directive = els.directiveInput.value.trim();
    if (!directive) return alert("Please enter a directive.");

    els.btnStart.disabled = true;
    els.btnStart.innerHTML = `<span class="animate-spin">⌛</span> Initializing...`;

    try {
        const res = await apiCall("/runs", "POST", { directive });
        state.runId = res.run_id;
        
        // Hide setup, show pipeline
        els.setupPanel.classList.add("hidden");
        els.pipelineContainer.classList.remove("hidden");
        
        // Start polling loop
        pollState();
    } catch (e) {
        els.btnStart.disabled = false;
        els.btnStart.innerText = "Initialize Run";
    }
}

async function runStage(stageName) {
    updateStatus(`Executing ${stageName}...`);
    try {
        await apiCall(`/runs/${state.runId}/reflex/${stageName}`, "POST");
        // Polling will catch the update
    } catch (e) {
        console.error(e);
    }
}

async function runBaseline() {
    updateStatus("Running Baseline...");
    try {
        await apiCall(`/runs/${state.runId}/baseline`, "POST");
    } catch (e) {
        console.error(e);
    }
}

async function pollState() {
    if (!state.runId) return;

    try {
        // Fetch full state including provenance for the viewer
        const data = await apiCall(`/runs/${state.runId}/state?include_provenance=true`);
        state.data = data;
        renderPipeline();
        updateStatus("System Idle");
    } catch (e) {
        // Stop polling on critical error? No, retry.
    }

    // Poll every 2 seconds
    setTimeout(pollState, 2000);
}

// --- RENDERING ---

function renderPipeline() {
    const container = els.pipelineContainer;
    container.innerHTML = ""; // Full re-render for simplicity (robustness)

    // 1. BASELINE CARD
    const bl = state.data.baseline;
    const blCard = createStageCard("baseline", "Consumer Baseline", bl);
    container.appendChild(blCard);

    // 2. PIPELINE STAGES
    STAGE_ORDER.forEach(stageKey => {
        const stageData = state.data.stages[stageKey];
        const card = createStageCard(stageKey, STAGE_LABELS[stageKey], stageData);
        container.appendChild(card);
    });
}

function createStageCard(key, label, stageState) {
    const div = document.createElement('div');
    div.className = `pipeline-step bg-slate-800 border border-slate-700 rounded-lg p-4 transition-all hover:border-slate-600`;
    
    // Status Logic
    let statusColor = "bg-slate-600";
    let icon = "circle";
    let btn = "";

    if (stageState.status === "completed") {
        statusColor = "bg-emerald-500";
        icon = "check-circle";
    } else if (stageState.status === "running") {
        statusColor = "bg-amber-500 animate-pulse";
        icon = "loader";
    } else if (stageState.status === "failed") {
        statusColor = "bg-red-500";
        icon = "x-circle";
    }

    // Interaction Logic
    const isNext = isStageNext(key);
    if (stageState.status === "pending" && isNext) {
        btn = `<button onclick="${key === 'baseline' ? 'runBaseline()' : `runStage('${key}')`}" 
               class="mt-3 w-full py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded transition-colors">
               RUN STAGE
               </button>`;
    } else if (stageState.status === "running") {
        btn = `<div class="mt-3 text-xs text-amber-500 font-mono animate-pulse">PROCESSING...</div>`;
    }

    // View Logic
    const clickView = `viewOutput('${key}')`;

    div.innerHTML = `
        <div class="flex items-start gap-3 relative z-10">
            <div class="mt-1 w-3 h-3 rounded-full ${statusColor} shadow-lg shrink-0"></div>
            <div class="flex-1">
                <div class="flex justify-between items-center cursor-pointer" onclick="${clickView}">
                    <h3 class="text-sm font-semibold text-slate-200">${label}</h3>
                    <i data-lucide="${icon}" class="w-4 h-4 text-slate-500"></i>
                </div>
                ${stageState.error ? `<p class="text-xs text-red-400 mt-1">${stageState.error}</p>` : ''}
                ${btn}
            </div>
        </div>
    `;
    
    // Initialize icons for this element
    setTimeout(() => lucide.createIcons(), 0);
    return div;
}

function isStageNext(key) {
    // Baseline is always available to run if pending
    if (key === 'baseline') return state.data.baseline.status === 'pending';

    const idx = STAGE_ORDER.indexOf(key);
    if (idx === 0) return true; // First stage always runnable if pending

    // Check previous stage
    const prevKey = STAGE_ORDER[idx - 1];
    return state.data.stages[prevKey].status === 'completed';
}

function viewOutput(key) {
    // 1. Get Data
    let stageData = key === 'baseline' ? state.data.baseline : state.data.stages[key];
    
    // 2. Set Title
    els.viewerTitle.innerText = key === 'baseline' ? "Baseline Output" : STAGE_LABELS[key];

    // 3. Render Content
    if (!stageData || !stageData.data) {
        els.viewerContent.innerHTML = `<div class="text-slate-500 italic">No output data available yet.</div>`;
        return;
    }

    const showProv = els.toggleProv.checked;
    
    let html = "";

    // MAIN DATA (Pretty Print JSON)
    html += `<div class="mb-6">
                <h4 class="text-xs font-bold text-indigo-400 uppercase mb-2">Primary Output</h4>
                <pre class="bg-slate-900 p-4 rounded-lg border border-slate-800 text-xs overflow-x-auto">${syntaxHighlight(stageData.data)}</pre>
             </div>`;

    // PROVENANCE
    if (showProv && stageData.provenance) {
        html += `<div class="border-t border-slate-800 pt-6 animate-fade-in">
                    <h4 class="text-xs font-bold text-slate-500 uppercase mb-2">Provenance (Meta-Data)</h4>
                    <div class="grid grid-cols-2 gap-4 text-xs text-slate-400 mb-4">
                        <div><span class="text-slate-600">Model:</span> ${stageData.provenance.model_name}</div>
                        <div><span class="text-slate-600">Time:</span> ${new Date(stageData.provenance.timestamp).toLocaleTimeString()}</div>
                        <div><span class="text-slate-600">Repair Attempts:</span> ${stageData.provenance.repair_attempts}</div>
                    </div>
                    <div class="mb-2 text-xs text-slate-600">Raw Prompt:</div>
                    <pre class="bg-slate-900/50 p-2 rounded text-[10px] text-slate-500 whitespace-pre-wrap">${stageData.provenance.prompt}</pre>
                 </div>`;
    }

    els.viewerContent.innerHTML = html;
}

// Utility: JSON Syntax Highlighting
function syntaxHighlight(json) {
    if (typeof json != 'string') {
         json = JSON.stringify(json, undefined, 2);
    }
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        var cls = 'number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'key';
            } else {
                cls = 'string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'boolean';
        } else if (/null/.test(match)) {
            cls = 'null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

function updateStatus(msg) {
    els.statusBar.innerText = `STATUS: ${msg.toUpperCase()}`;
}

function showError(msg) {
    alert(msg); // Simple, as requested
}

// --- INIT ---
els.btnStart.addEventListener('click', createRun);
els.toggleProv.addEventListener('change', () => {
    // Re-render current view if possible, loosely
    const title = els.viewerTitle.innerText;
    // This is a lazy re-render: User clicks stage again to refresh or we add state tracking for currentView.
    // For now, let's keep it simple: next click updates it.
});

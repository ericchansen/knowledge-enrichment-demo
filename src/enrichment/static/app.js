/* Side-by-side comparison chat UI */

const API_BASE = "";  // Same origin

const baselineChat = document.getElementById("baseline-chat");
const enhancedChat = document.getElementById("enhanced-chat");
const queryInput = document.getElementById("query-input");
const sendBtn = document.getElementById("send-btn");

// Enter key sends query
queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !sendBtn.disabled) sendQuery();
});

function askSample(btn) {
    queryInput.value = btn.textContent;
    sendQuery();
}

async function sendQuery() {
    const message = queryInput.value.trim();
    if (!message) return;

    sendBtn.disabled = true;
    queryInput.value = "";

    // Clear placeholders
    clearPlaceholders();

    // Add user messages to both panels
    appendMessage(baselineChat, message, "user");
    appendMessage(enhancedChat, message, "user");

    // Show loading indicators
    const baselineLoading = appendLoading(baselineChat);
    const enhancedLoading = appendLoading(enhancedChat);

    try {
        const startBaseline = performance.now();
        const startEnhanced = performance.now();

        // Fire both requests in parallel
        const [baselineRes, enhancedRes] = await Promise.all([
            fetchChat("/api/chat/baseline", message),
            fetchChat("/api/chat/enhanced", message),
        ]);

        const baselineTime = performance.now() - startBaseline;
        const enhancedTime = performance.now() - startEnhanced;

        // Remove loading indicators
        baselineLoading.remove();
        enhancedLoading.remove();

        // Display results
        appendAssistantMessage(baselineChat, baselineRes, false);
        appendAssistantMessage(enhancedChat, enhancedRes, true);

        // Update stats
        updateStats(baselineRes, enhancedRes, baselineTime, enhancedTime);

    } catch (err) {
        baselineLoading.remove();
        enhancedLoading.remove();
        appendMessage(baselineChat, `Error: ${err.message}`, "assistant");
        appendMessage(enhancedChat, `Error: ${err.message}`, "assistant");
    } finally {
        sendBtn.disabled = false;
        queryInput.focus();
    }
}

async function fetchChat(endpoint, message) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
    });
    if (!response.ok) {
        const text = await response.text();
        throw new Error(`${response.status}: ${text}`);
    }
    return response.json();
}

function clearPlaceholders() {
    baselineChat.querySelectorAll(".placeholder").forEach((el) => el.remove());
    enhancedChat.querySelectorAll(".placeholder").forEach((el) => el.remove());
}

function appendMessage(container, text, role) {
    const div = document.createElement("div");
    div.className = `msg ${role}`;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

function appendLoading(container) {
    const div = document.createElement("div");
    div.className = "loading";
    div.textContent = "Thinking…";
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

function appendAssistantMessage(container, data, isEnhanced) {
    const div = document.createElement("div");
    div.className = `msg assistant${isEnhanced ? " enhanced-msg" : ""}`;

    // Message text
    const textP = document.createElement("p");
    textP.textContent = data.message || "No response";
    div.appendChild(textP);

    // Citations
    if (data.citations && data.citations.length > 0) {
        const citDiv = document.createElement("div");
        citDiv.className = "citations";
        citDiv.innerHTML = `<strong>Citations (${data.citations.length}):</strong> ` +
            data.citations
                .map((c) => {
                    if (c.report_title && c.report_number) {
                        return `${c.report_title} (${c.report_number})`;
                    }
                    return c.document_id;
                })
                .filter((v, i, a) => a.indexOf(v) === i)  // unique
                .join(", ");
        div.appendChild(citDiv);
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function updateStats(baselineRes, enhancedRes, baselineTime, enhancedTime) {
    document.getElementById("stats-bar").style.display = "flex";
    document.getElementById("stat-baseline-citations").textContent =
        (baselineRes.citations || []).length;
    document.getElementById("stat-enhanced-citations").textContent =
        (enhancedRes.citations || []).length;
    document.getElementById("stat-baseline-time").textContent =
        `${(baselineTime / 1000).toFixed(1)}s`;
    document.getElementById("stat-enhanced-time").textContent =
        `${(enhancedTime / 1000).toFixed(1)}s`;
}

// ── Corpus & Pipeline management ──────────────────────────

async function loadCorpus() {
    try {
        const res = await fetch(`${API_BASE}/api/corpus`);
        const data = await res.json();
        document.getElementById("corpus-count").textContent =
            `${data.total_documents} document${data.total_documents !== 1 ? "s" : ""}`;
        const list = document.getElementById("corpus-list");
        list.innerHTML = "";
        for (const doc of data.documents || []) {
            const li = document.createElement("li");
            li.textContent = doc.filename;
            list.appendChild(li);
        }
    } catch { /* ignore on load */ }
}

async function uploadFiles() {
    const input = document.getElementById("file-upload");
    if (!input.files || input.files.length === 0) return;

    const statusEl = document.getElementById("pipeline-status");
    statusEl.style.display = "block";
    statusEl.className = "pipeline-status";
    statusEl.textContent = `Uploading ${input.files.length} file(s)…`;

    let uploaded = 0;
    for (const file of input.files) {
        const form = new FormData();
        form.append("file", file);
        try {
            await fetch(`${API_BASE}/api/corpus/upload`, { method: "POST", body: form });
            uploaded++;
        } catch (err) {
            statusEl.className = "pipeline-status error";
            statusEl.textContent = `Error uploading ${file.name}: ${err.message}`;
            return;
        }
    }

    statusEl.className = "pipeline-status complete";
    statusEl.textContent = `Uploaded ${uploaded} file(s).`;
    input.value = "";
    loadCorpus();
}

async function runPipeline(type) {
    const btn = document.getElementById(type === "baseline" ? "btn-run-baseline" : "btn-run-enhanced");
    const statusEl = document.getElementById("pipeline-status");

    btn.disabled = true;
    statusEl.style.display = "block";
    statusEl.className = "pipeline-status";
    statusEl.textContent = `Running ${type} pipeline… This may take a few minutes.`;

    try {
        const res = await fetch(`${API_BASE}/api/pipeline/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pipeline_type: type }),
        });
        const data = await res.json();

        if (data.status === "complete") {
            statusEl.className = "pipeline-status complete";
            statusEl.textContent = `✓ ${data.message}`;
        } else {
            statusEl.className = "pipeline-status error";
            statusEl.textContent = `✗ ${data.message}`;
        }
    } catch (err) {
        statusEl.className = "pipeline-status error";
        statusEl.textContent = `Error: ${err.message}`;
    } finally {
        btn.disabled = false;
    }
}

// Load corpus on page load
loadCorpus();

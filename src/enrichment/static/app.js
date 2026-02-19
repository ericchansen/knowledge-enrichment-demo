/* Side-by-side comparison chat UI */

const API_BASE = "";  // Same origin

const baselineChat = document.getElementById("baseline-chat");
const enhancedChat = document.getElementById("enhanced-chat");
const queryInput = document.getElementById("query-input");
const sendBtn = document.getElementById("send-btn");

queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !sendBtn.disabled) sendQuery();
});

function askSample(btn) {
    queryInput.value = btn.textContent;
    sendQuery();
}

// ── Lightweight Markdown → HTML ─────────────────────────────

function md(text) {
    if (!text) return "";
    let html = text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        // Bold
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        // Italic
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        // Headings (### h3, ## h2)
        .replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
        .replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
        // Unordered lists
        .replace(/^[-•] (.+)$/gm, '<li>$1</li>')
        // Ordered lists
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        // Wrap consecutive <li> in <ul>
        .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul class="md-list">$1</ul>')
        // Line breaks (double newline = paragraph break)
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    return `<p>${html}</p>`;
}

// ── Chat Flow ───────────────────────────────────────────────

async function sendQuery() {
    const message = queryInput.value.trim();
    if (!message) return;

    sendBtn.disabled = true;
    queryInput.value = "";
    clearPlaceholders();

    appendMessage(baselineChat, message, "user");
    appendMessage(enhancedChat, message, "user");

    const baselineLoading = appendLoading(baselineChat);
    const enhancedLoading = appendLoading(enhancedChat);

    try {
        const startBaseline = performance.now();
        const startEnhanced = performance.now();

        const [baselineRes, enhancedRes] = await Promise.all([
            fetchChat("/api/chat/baseline", message),
            fetchChat("/api/chat/enhanced", message),
        ]);

        const baselineTime = performance.now() - startBaseline;
        const enhancedTime = performance.now() - startEnhanced;

        baselineLoading.remove();
        enhancedLoading.remove();

        appendAssistantMessage(baselineChat, baselineRes, false);
        appendAssistantMessage(enhancedChat, enhancedRes, true);

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

// ── Message Rendering ───────────────────────────────────────

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

    // Metadata card (enhanced only, when metadata exists)
    const meta = data.metadata || {};
    if (isEnhanced && meta.reports && meta.reports.length > 0) {
        const card = document.createElement("div");
        card.className = "metadata-card";

        // Reports
        const reportsHtml = meta.reports.map(r =>
            `<div class="meta-report"><span class="meta-number">${esc(r.number)}</span> ${esc(r.title)}</div>`
        ).join("");

        // Agencies
        const agenciesHtml = (meta.agencies || []).map(a =>
            `<span class="meta-tag agency-tag">${esc(a)}</span>`
        ).join("");

        // Topics
        const topicsHtml = (meta.topics || []).map(t =>
            `<span class="meta-tag topic-tag">${esc(t)}</span>`
        ).join("");

        let inner = `<div class="meta-label">📊 Source Intelligence</div>`;
        inner += `<div class="meta-reports">${reportsHtml}</div>`;
        if (agenciesHtml) inner += `<div class="meta-section"><span class="meta-section-label">Agencies:</span> ${agenciesHtml}</div>`;
        if (topicsHtml) inner += `<div class="meta-section"><span class="meta-section-label">Topics:</span> ${topicsHtml}</div>`;

        card.innerHTML = inner;
        div.appendChild(card);
    }

    // Message body (rendered markdown)
    const bodyDiv = document.createElement("div");
    bodyDiv.className = "msg-body";
    bodyDiv.innerHTML = md(data.message || "No response");
    div.appendChild(bodyDiv);

    // Citations
    if (data.citations && data.citations.length > 0) {
        const citDiv = document.createElement("div");
        citDiv.className = "citations";

        if (isEnhanced) {
            // Rich citation cards
            const unique = dedupeByReport(data.citations);
            citDiv.innerHTML = `<div class="cit-label">📎 Sources (${unique.length})</div>` +
                unique.map(c => {
                    const pct = Math.round((c.score || 0) * 100 * 30); // scale for visual
                    const barW = Math.min(Math.max(pct, 8), 100);
                    return `<div class="cit-card">
                        <div class="cit-header">
                            <span class="cit-number">${esc(c.report_number || c.document_id)}</span>
                            <span class="cit-title">${esc(c.report_title || "")}</span>
                        </div>
                        <div class="cit-score-bar"><div class="cit-score-fill" style="width:${barW}%"></div></div>
                        <div class="cit-snippet">${esc(c.snippet || "")}</div>
                    </div>`;
                }).join("");
        } else {
            // Simple baseline citations — just doc IDs
            const ids = [...new Set(data.citations.map(c => c.document_id))];
            citDiv.innerHTML = `<div class="cit-label">📎 Sources (${ids.length})</div>` +
                ids.map(id => `<span class="cit-id">${esc(id)}</span>`).join(" ");
        }
        div.appendChild(citDiv);
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function dedupeByReport(citations) {
    const seen = new Set();
    return citations.filter(c => {
        const key = c.report_number || c.document_id;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

function esc(s) {
    const el = document.createElement("span");
    el.textContent = s || "";
    return el.innerHTML;
}

// ── Stats Bar ───────────────────────────────────────────────

function updateStats(baselineRes, enhancedRes, baselineTime, enhancedTime) {
    document.getElementById("stats-bar").style.display = "flex";

    const bMeta = baselineRes.metadata || {};
    const eMeta = enhancedRes.metadata || {};

    const bReports = (bMeta.reports || []).length;
    const eReports = (eMeta.reports || []).length;
    const bAgencies = (bMeta.agencies || []).length;
    const eAgencies = (eMeta.agencies || []).length;

    setStat("stat-baseline-reports", bReports, false);
    setStat("stat-enhanced-reports", eReports, eReports > bReports);
    setStat("stat-baseline-agencies", bAgencies, false);
    setStat("stat-enhanced-agencies", eAgencies, eAgencies > bAgencies);
    setStat("stat-baseline-titles", bMeta.reports?.some(r => r.title) ? "✓" : "✗", false);
    setStat("stat-enhanced-titles", eMeta.reports?.some(r => r.title) ? "✓" : "✗", eMeta.reports?.some(r => r.title));
    document.getElementById("stat-baseline-time").textContent = `${(baselineTime / 1000).toFixed(1)}s`;
    document.getElementById("stat-enhanced-time").textContent = `${(enhancedTime / 1000).toFixed(1)}s`;
}

function setStat(id, value, highlight) {
    const el = document.getElementById(id);
    el.textContent = value;
    el.className = `stat-value${highlight ? " stat-winner" : ""}`;
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

loadCorpus();

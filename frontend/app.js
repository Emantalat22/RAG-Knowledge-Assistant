// -----------------------------------------------------------------
// RAG Knowledge Assistant -- frontend logic
//
// Every function in this file talks to the existing FastAPI backend
// (fastapi_app.py) over HTTP. No answers, sources, or document data
// are generated here -- this file only renders whatever the backend
// returns.
// -----------------------------------------------------------------

const API_BASE_URL = CONFIG.API_BASE_URL;

// ---- DOM references ----
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const uploadProgress = document.getElementById("uploadProgress");
const uploadProgressLabel = document.getElementById("uploadProgressLabel");

const docList = document.getElementById("docList");
const docListEmpty = document.getElementById("docListEmpty");
const statRow = document.getElementById("statRow");
const chunkCountEl = document.getElementById("chunkCount");

const reindexBtn = document.getElementById("reindexBtn");
const clearBtn = document.getElementById("clearBtn");

const chatTranscript = document.getElementById("chatTranscript");
const emptyState = document.getElementById("emptyState");
const chatForm = document.getElementById("chatForm");
const questionInput = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");

const statusPill = document.getElementById("statusPill");
const statusDot = document.getElementById("statusDot");
const statusLabel = document.getElementById("statusLabel");

const userMessageTemplate = document.getElementById("userMessageTemplate");
const assistantMessageTemplate = document.getElementById("assistantMessageTemplate");
const loadingMessageTemplate = document.getElementById("loadingMessageTemplate");
const errorMessageTemplate = document.getElementById("errorMessageTemplate");

let isBusy = false;

// ===================================================================
// Backend health
// ===================================================================

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    const data = await res.json();

    if (data.status === "ok") {
      statusPill.dataset.state = "ok";
      statusLabel.textContent = "Backend connected";
      if (typeof data.chunks_indexed === "number") {
        updateChunkCount(data.chunks_indexed);
      }
    } else {
      statusPill.dataset.state = "error";
      statusLabel.textContent = "Backend error";
    }
  } catch (err) {
    statusPill.dataset.state = "error";
    statusLabel.textContent = "Backend unreachable";
  }
}

// ===================================================================
// Documents
// ===================================================================

async function loadDocuments() {
  try {
    const res = await fetch(`${API_BASE_URL}/documents`);
    const data = await res.json();

    if (data.error) {
      console.error(data.error);
      return;
    }

    renderDocumentList(data.documents || []);
  } catch (err) {
    // Silent -- the status pill already communicates backend reachability.
  }
}

function renderDocumentList(filenames) {
  docList.querySelectorAll(".doc-chip").forEach((el) => el.remove());

  if (!filenames.length) {
    docListEmpty.hidden = false;
    return;
  }

  docListEmpty.hidden = true;

  filenames.forEach((name) => {
    const li = document.createElement("li");
    li.className = "doc-chip";
    li.innerHTML = `
      <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 2h5l3 3v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><path d="M9 2v3h3" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>
      <span class="doc-chip-name"></span>
    `;
    li.querySelector(".doc-chip-name").textContent = name;
    docList.appendChild(li);
  });
}

function updateChunkCount(count) {
  statRow.hidden = false;
  chunkCountEl.textContent = count;
}

// ===================================================================
// Upload
// ===================================================================

async function uploadFile(file) {
  if (!file) return;

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    appendErrorMessage("Only PDF files are allowed.");
    return;
  }

  uploadProgress.hidden = false;
  uploadProgressLabel.textContent = "Uploading and indexing\u2026";
  dropzone.setAttribute("aria-busy", "true");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (data.error) {
      appendErrorMessage(data.error);
    } else {
      if (typeof data.chunks_indexed === "number") {
        updateChunkCount(data.chunks_indexed);
      }
      await loadDocuments();
    }
  } catch (err) {
    appendErrorMessage(
      `Could not reach the backend at ${API_BASE_URL}. Make sure fastapi_app.py is running.`
    );
  } finally {
    uploadProgress.hidden = true;
    dropzone.removeAttribute("aria-busy");
  }
}

// dropzone interactions
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) uploadFile(fileInput.files[0]);
  fileInput.value = "";
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);

["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);

dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

// ===================================================================
// Re-index
// ===================================================================

reindexBtn.addEventListener("click", async () => {
  reindexBtn.disabled = true;
  const originalHTML = reindexBtn.innerHTML;
  reindexBtn.innerHTML = "Re-indexing\u2026";

  try {
    const res = await fetch(`${API_BASE_URL}/reindex`, { method: "POST" });
    const data = await res.json();

    if (data.error) {
      appendErrorMessage(data.error);
    } else {
      if (typeof data.chunks_indexed === "number") {
        updateChunkCount(data.chunks_indexed);
      }
      await loadDocuments();
    }
  } catch (err) {
    appendErrorMessage(
      `Could not reach the backend at ${API_BASE_URL}. Make sure fastapi_app.py is running.`
    );
  } finally {
    reindexBtn.disabled = false;
    reindexBtn.innerHTML = originalHTML;
  }
});

// ===================================================================
// Chat
// ===================================================================

function scrollToBottom() {
  chatTranscript.scrollTop = chatTranscript.scrollHeight;
}

function hideEmptyState() {
  emptyState.hidden = true;
}

function appendUserMessage(text) {
  hideEmptyState();
  const node = userMessageTemplate.content.cloneNode(true);
  node.querySelector(".msg-bubble").textContent = text;
  chatTranscript.appendChild(node);
  scrollToBottom();
}

function appendLoadingMessage() {
  hideEmptyState();
  const node = loadingMessageTemplate.content.cloneNode(true);
  const el = node.querySelector(".msg-loading");
  chatTranscript.appendChild(node);
  scrollToBottom();
  return chatTranscript.lastElementChild;
}

function appendAssistantMessage(answer, sources) {
  hideEmptyState();
  const node = assistantMessageTemplate.content.cloneNode(true);
  node.querySelector(".msg-bubble").textContent = answer;

  const sourcesEl = node.querySelector(".msg-sources");

  if (sources && sources.length) {
    sourcesEl.hidden = false;

    const label = document.createElement("div");
    label.className = "msg-sources-label";
    label.textContent = "Sources";
    sourcesEl.appendChild(label);

    sources.forEach((src, i) => {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      tag.innerHTML = `
        <span class="source-index">${i + 1}</span>
        <span class="source-file"></span>
        <span class="source-page"></span>
      `;
      tag.querySelector(".source-file").textContent = src.source;
      tag.querySelector(".source-page").textContent = `p. ${src.page}`;
      sourcesEl.appendChild(tag);
    });
  }

  chatTranscript.appendChild(node);
  scrollToBottom();
}

function appendErrorMessage(message) {
  hideEmptyState();
  const node = errorMessageTemplate.content.cloneNode(true);
  node.querySelector(".error-text").textContent = message;
  chatTranscript.appendChild(node);
  scrollToBottom();
}

async function askQuestion(question) {
  isBusy = true;
  sendBtn.disabled = true;

  appendUserMessage(question);
  const loadingEl = appendLoadingMessage();

  try {
    const res = await fetch(`${API_BASE_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    loadingEl.remove();

    if (data.error) {
      appendErrorMessage(data.error);
    } else {
      appendAssistantMessage(data.answer, data.sources);
    }
  } catch (err) {
    loadingEl.remove();
    appendErrorMessage(
      `Could not reach the backend at ${API_BASE_URL}. Make sure fastapi_app.py is running.`
    );
  } finally {
    isBusy = false;
    sendBtn.disabled = false;
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (isBusy) return;

  const question = questionInput.value.trim();
  if (!question) return;

  questionInput.value = "";
  questionInput.style.height = "auto";
  askQuestion(question);
});

// Enter to send, Shift+Enter for newline
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

// auto-grow textarea
questionInput.addEventListener("input", () => {
  questionInput.style.height = "auto";
  questionInput.style.height = Math.min(questionInput.scrollHeight, 140) + "px";
});

// ===================================================================
// Clear conversation
// ===================================================================

clearBtn.addEventListener("click", () => {
  chatTranscript.querySelectorAll(".msg").forEach((el) => el.remove());
  emptyState.hidden = false;
});

// ===================================================================
// Init
// ===================================================================

checkHealth();
loadDocuments();
setInterval(checkHealth, 15000);

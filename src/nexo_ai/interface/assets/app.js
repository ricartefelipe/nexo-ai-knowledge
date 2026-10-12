const readiness = document.querySelector("#readiness");
const uploadForm = document.querySelector("#upload-form");
const uploadButton = document.querySelector("#upload-button");
const fileInput = document.querySelector("#file");
const documentResult = document.querySelector("#document-result");
const queryForm = document.querySelector("#query-form");
const queryButton = document.querySelector("#query-button");
const questionInput = document.querySelector("#question");
const queryResult = document.querySelector("#query-result");

const statusLabels = {
  received: "Recebido",
  extracted: "Extraído",
  chunked: "Fragmentado",
  embedded: "Indexado",
  failed: "Falha",
};

function clear(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function paragraph(className, text) {
  const element = document.createElement("p");
  element.className = className;
  element.textContent = text;
  return element;
}

function showMessage(node, text) {
  clear(node);
  node.appendChild(paragraph("message", text));
}

async function problemDetail(response) {
  try {
    const body = await response.json();
    if (body && typeof body.detail === "string" && body.detail !== "") {
      return body.detail;
    }
  } catch {
    return "A operação falhou.";
  }
  return "A operação falhou.";
}

function statusLabel(status) {
  if (typeof status === "string" && Object.hasOwn(statusLabels, status)) {
    return statusLabels[status];
  }
  return "Estado desconhecido";
}

function showDocument(documentState) {
  clear(documentResult);
  const card = document.createElement("div");
  card.className = "card";
  const list = document.createElement("dl");
  const rows = [
    ["Arquivo", documentState.filename],
    ["Estado", statusLabel(documentState.status)],
    ["Fragmentos", String(documentState.chunk_count)],
  ];
  if (typeof documentState.failure_detail === "string" && documentState.failure_detail !== "") {
    rows.push(["Falha", documentState.failure_detail]);
  }
  for (const [label, value] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    description.textContent = typeof value === "string" ? value : "";
    list.appendChild(term);
    list.appendChild(description);
  }
  card.appendChild(list);
  documentResult.appendChild(card);
}

function showAnswer(payload) {
  clear(queryResult);
  const answer = paragraph("excerpt", typeof payload.answer === "string" ? payload.answer : "");
  queryResult.appendChild(answer);
  const grounding = paragraph(
    "meta",
    payload.grounded === true ? "Resposta com fontes indexadas." : "Nenhuma fonte foi usada.",
  );
  queryResult.appendChild(grounding);
  if (!Array.isArray(payload.references) || payload.references.length === 0) {
    return;
  }
  for (const source of payload.references) {
    if (!source || typeof source !== "object") {
      continue;
    }
    const card = document.createElement("article");
    card.className = "source";
    const title = document.createElement("h3");
    title.textContent = typeof source.filename === "string" ? source.filename : "Arquivo";
    const meta = paragraph(
      "meta",
      `Posição ${String(source.position)} · distância ${String(source.distance)}`,
    );
    const excerpt = paragraph("excerpt", typeof source.content === "string" ? source.content : "");
    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(excerpt);
    queryResult.appendChild(card);
  }
}

async function refreshReadiness() {
  try {
    const response = await fetch("/health/ready");
    if (response.ok) {
      readiness.textContent = "Banco disponível.";
      readiness.className = "readiness ready";
      return;
    }
    readiness.textContent = await problemDetail(response);
    readiness.className = "readiness failed";
  } catch {
    readiness.textContent = "Não foi possível falar com a API.";
    readiness.className = "readiness failed";
  }
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files && fileInput.files[0];
  if (!file) {
    showMessage(documentResult, "Selecione um arquivo.");
    return;
  }
  const body = new FormData();
  body.append("file", file);
  uploadButton.disabled = true;
  try {
    const response = await fetch("/api/v1/documents", { method: "POST", body });
    if (!response.ok) {
      showMessage(documentResult, await problemDetail(response));
      return;
    }
    showDocument(await response.json());
  } catch {
    showMessage(documentResult, "Não foi possível falar com a API.");
  } finally {
    uploadButton.disabled = false;
  }
});

queryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (question === "") {
    showMessage(queryResult, "A pergunta está vazia.");
    return;
  }
  queryButton.disabled = true;
  try {
    const response = await fetch("/api/v1/queries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) {
      showMessage(queryResult, await problemDetail(response));
      return;
    }
    showAnswer(await response.json());
  } catch {
    showMessage(queryResult, "Não foi possível falar com a API.");
  } finally {
    queryButton.disabled = false;
  }
});

refreshReadiness();

(() => {
  const root = document.body;
  if (!root || !root.dataset.lessonId || !root.dataset.activityId) return;

  const lessonId = root.dataset.lessonId;
  const activityId = root.dataset.activityId;
  const stateKey = stateKeyFromIds(lessonId, activityId) || `tlac_${lessonId}_${activityId}_state`;

  const codeEditor = document.getElementById("codeEditor");
  const runBtn = document.getElementById("runBtn");
  const saveFilesBtn = document.getElementById("saveFilesBtn");
  const resetBtn = document.getElementById("resetBtn");
  const stdoutEl = document.getElementById("stdout");
  const stderrEl = document.getElementById("stderr");
  const runMetaEl = document.getElementById("runMeta");
  const runFilesEl = document.getElementById("runFiles");
  const savedFilesEl = document.getElementById("savedFiles");

  function initFloatingEditor(){
    if(!codeEditor || !runBtn) return;
    const editorCard = codeEditor.closest(".card");
    if(!editorCard) return;
    const container = editorCard.closest(".container");
    if(!container || container.dataset.codeLayout === "1") return;
    container.dataset.codeLayout = "1";

    const layout = document.createElement("div");
    layout.className = "code-layout";
    const main = document.createElement("div");
    main.className = "code-main";
    const side = document.createElement("div");
    side.className = "code-side";

    const children = Array.from(container.children);
    children.forEach(child => main.appendChild(child));
    layout.appendChild(main);
    layout.appendChild(side);
    container.appendChild(layout);

    const panel = document.createElement("div");
    panel.className = "card code-panel";
    const title = document.createElement("h2");
    title.textContent = "Code editor";
    panel.appendChild(title);

    const editorParent = codeEditor.parentElement;
    const editorNext = codeEditor.nextSibling;
    const editorNote = Array.from(editorCard.children).find(el => el.classList && el.classList.contains("note"));
    if(editorNote){
      panel.appendChild(editorNote);
    }

    panel.appendChild(codeEditor);
    const runRow = runBtn.closest(".row");
    if(runRow){
      panel.appendChild(runRow);
    }
    side.appendChild(panel);

    if(editorParent){
      const placeholder = document.createElement("div");
      placeholder.className = "note";
      placeholder.innerHTML = "<b>Editor panel:</b> The code editor and buttons are on the right.";
      editorParent.insertBefore(placeholder, editorNext || null);
    }
  }

  const DEFAULT_CODE = [
    "# Python runner demo",
    "name = \"Coder\"",
    "print(\"Hello\", name)",
    "# Try file I/O:",
    "with open(\"notes.txt\", \"w\") as f:",
    "    f.write(\"My first saved file!\")",
    "print(\"File written.\")",
    "# Turtle demo (SVG output):",
    "# import turtle",
    "# turtle.forward(80)",
    "# turtle.left(90)",
    "# turtle.forward(80)",
  ].join("\n");

  const state = store.get(stateKey, {
    code: DEFAULT_CODE,
    output: null,
    answers: {},
    checked: {},
    notes: {},
    files: []
  });

  let runFiles = [];
  initFloatingEditor();

  function decodeBase64Text(value){
    try{
      const binary = atob(value || "");
      const bytes = Uint8Array.from(binary, ch => ch.charCodeAt(0));
      return new TextDecoder("utf-8").decode(bytes);
    }catch{
      return "";
    }
  }

  function renderRunMeta(output){
    if (!output){
      runMetaEl.style.display = "none";
      return;
    }
    const status = output.timed_out ? "Timed out" : "Completed";
    runMetaEl.innerHTML = `<b>${status}</b> · Exit code: ${output.exit_code ?? "?"} · ${output.duration_ms || 0}ms`;
    runMetaEl.style.display = "";
  }

  function renderOutput(output){
    stdoutEl.textContent = output && output.stdout ? output.stdout : "";
    stderrEl.textContent = output && output.stderr ? output.stderr : "";
    renderRunMeta(output);
  }

  function showRunnerError(detail){
    const message = detail || "Runner unavailable.";
    if(stderrEl) stderrEl.textContent = message;
    if(runMetaEl){
      runMetaEl.textContent = "Runner error. See stderr for details.";
      runMetaEl.style.display = "";
    }
    console.error(message);
  }

  function renderFiles(host, files, label){
    host.innerHTML = "";
    if(!files || !files.length){
      host.innerHTML = `<small class=\"muted\">${label}</small>`;
      return;
    }

    files.forEach(file => {
      const card = document.createElement("div");
      card.className = "file-card";
      const header = document.createElement("div");
      header.innerHTML = `<b>${escapeHtml(file.path)}</b> <small class=\"muted\">${file.size} bytes</small>`;
      card.appendChild(header);

      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "View file";
      details.appendChild(summary);

      if(file.mime && file.mime.startsWith("image/")){
        const img = document.createElement("img");
        img.className = "file-preview";
        img.alt = file.path;
        img.src = `data:${file.mime};base64,${file.content_base64}`;
        details.appendChild(img);
      }else{
        const pre = document.createElement("pre");
        pre.className = "code-output";
        pre.textContent = decodeBase64Text(file.content_base64);
        details.appendChild(pre);
      }

      card.appendChild(details);
      host.appendChild(card);
    });
  }

  function saveState(){
    store.set(stateKey, state);
  }

  function initQuizzes(){
    root.querySelectorAll("[data-quiz]").forEach(quiz => {
      const quizId = quiz.dataset.quiz;
      const stored = state.answers[quizId];
      if(stored){
        const input = quiz.querySelector(`input[type='radio'][value='${stored}']`);
        if(input) input.checked = true;
      }
      quiz.querySelectorAll("input[type='radio']").forEach(input => {
        input.addEventListener("change", () => {
          state.answers[quizId] = input.value;
          saveState();
        });
      });
    });

    root.querySelectorAll("[data-quiz-check]").forEach(btn => {
      btn.addEventListener("click", () => {
        const quizId = btn.dataset.quizCheck;
        const quiz = root.querySelector(`[data-quiz='${quizId}']`);
        const feedback = root.querySelector(`[data-quiz-feedback='${quizId}']`);
        if(!quiz || !feedback) return;
        const correct = quiz.dataset.correct;
        const answer = state.answers[quizId];
        if(!answer){
          feedback.style.display = "";
          feedback.className = "note warn";
          feedback.innerHTML = "<b>Pick an answer first.</b>";
          return;
        }
        const ok = answer === correct;
        state.checked[quizId] = ok;
        saveState();
        feedback.style.display = "";
        feedback.className = `note ${ok ? "good" : "warn"}`;
        feedback.innerHTML = ok ? "<b>Correct.</b>" : "<b>Not quite.</b> Try again.";
      });
    });
  }

  function initNotes(){
    root.querySelectorAll("[data-field]").forEach(el => {
      const key = el.dataset.field;
      if(state.notes[key]){
        el.value = state.notes[key];
      }
      el.addEventListener("input", () => {
        state.notes[key] = el.value;
        saveState();
      });
    });
  }

  async function runCode(){
    if(!navigator.onLine){
      toast("You are offline. Reconnect to run code.");
      return;
    }
    const auth = window.tlacAuthReady ? await window.tlacAuthReady : null;
    if(!auth || !auth.csrf_token){
      toast("Login required to run code.");
      return;
    }

    runBtn.disabled = true;
    runBtn.textContent = "Running...";
    stdoutEl.textContent = "";
    stderrEl.textContent = "";
    runMetaEl.style.display = "none";

    const payloadFiles = (state.files || [])
      .filter(file => {
        const mime = file.mime || "";
        return (
          mime.startsWith("text/") ||
          mime === "image/svg+xml" ||
          mime === "application/json" ||
          !mime
        );
      })
      .map(file => {
        const text = decodeBase64Text(file.content_base64 || "");
        return {
          path: file.path,
          content: text
        };
      });

    try{
      const res = await fetch("/api/python/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": auth.csrf_token
        },
        credentials: "same-origin",
        body: JSON.stringify({
          lesson_id: lessonId,
          activity_id: activityId,
          code: codeEditor.value,
          files: payloadFiles
        })
      });
      const rawText = await res.text().catch(()=> "");
      let data = {};
      if(rawText){
        try{
          data = JSON.parse(rawText);
        }catch{
          data = { detail: rawText };
        }
      }
      if(!res.ok){
        const detail = data && data.detail ? String(data.detail) : "Runner unavailable.";
        toast(detail);
        showRunnerError(detail);
        return;
      }
      state.code = codeEditor.value;
      state.output = {
        stdout: data.stdout || "",
        stderr: data.stderr || "",
        exit_code: data.exit_code,
        timed_out: data.timed_out,
        duration_ms: data.duration_ms,
        ran_at: new Date().toISOString()
      };
      saveState();
      renderOutput(state.output);
      runFiles = Array.isArray(data.files) ? data.files : [];
      renderFiles(runFilesEl, runFiles, "No run files yet.");
    }catch{
      const detail = "Runner error. Try again.";
      toast(detail);
      showRunnerError(detail);
    }finally{
      runBtn.disabled = false;
      runBtn.textContent = "Run code";
    }
  }

  function saveRunFiles(){
    if(!runFiles.length){
      toast("No run files to save.");
      return;
    }
    state.files = runFiles.slice(0, 20);
    saveState();
    renderFiles(savedFilesEl, state.files, "No saved files yet.");
    toast("Files saved to your attempt.");
  }

  function resetEditor(){
    if(!confirm("Reset code and output?")) return;
    state.code = DEFAULT_CODE;
    state.output = null;
    state.files = [];
    runFiles = [];
    saveState();
    codeEditor.value = state.code;
    renderOutput(state.output);
    renderFiles(runFilesEl, runFiles, "No run files yet.");
    renderFiles(savedFilesEl, state.files, "No saved files yet.");
  }

  codeEditor.value = state.code || DEFAULT_CODE;
  codeEditor.addEventListener("input", () => {
    state.code = codeEditor.value;
    saveState();
  });

  runBtn.addEventListener("click", runCode);
  saveFilesBtn.addEventListener("click", saveRunFiles);
  resetBtn.addEventListener("click", resetEditor);

  initQuizzes();
  initNotes();
  renderOutput(state.output);
  renderFiles(runFilesEl, runFiles, "No run files yet.");
  renderFiles(savedFilesEl, state.files, "No saved files yet.");
})();

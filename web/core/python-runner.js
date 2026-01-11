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

  let hintTemplateText = null;
  let hintTemplateStep = "code-step-1";

  function captureHintTemplate(){
    if(!codeEditor) return;
    const editorCard = codeEditor.closest(".card");
    if(!editorCard) return;
    if(!editorCard.dataset.hintLabel){
      const heading = editorCard.querySelector("h2, h3");
      if(heading){
        editorCard.dataset.hintLabel = heading.textContent.trim();
      }
    }
    let template = editorCard.querySelector("template[data-hint-code-template]");
    if(!template){
      template = document.querySelector("template[data-hint-code-template]");
    }
    if(!template) return;
    const text = template.textContent || "";
    const normalized = normalizeHintCode(text);
    if(!normalized.trim()) return;
    hintTemplateText = normalized;
    hintTemplateStep = template.dataset.hintCodeTemplate || "code-step-1";
  }

  function initFloatingEditor(){
    if(!codeEditor || !runBtn) return;
    const editorCard = codeEditor.closest(".card");
    if(!editorCard) return;
    if(!editorCard.dataset.hintLabel){
      const heading = editorCard.querySelector("h2, h3");
      if(heading){
        editorCard.dataset.hintLabel = heading.textContent.trim();
      }
    }
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

  const HINT_DEFAULT_CODE = [
    "# Starter skeleton (replace the TODOs)",
    "# Tip: keep your code small and test after each change.",
    "",
    "# TODO: replace this value with your own logic",
    "result = 0",
    "print(\"Result:\", result)",
  ].join("\n");

  const HINT_LIBRARY = {
    "lesson-10": {
      "a01": `
        age = 14

        if age < 13:
            print("Child")
        if age >= 13 and age < 18:
            print("Teen")
        if age >= 18:
            print("Adult")
`,
      "a02": `
        light = "red"

        if light == "red":
            action = "stop"
        elif light == "amber":
            action = "ready"
        elif light == "green":
            action = "go"
        else:
            action = "unknown"

        print(action)
`,
    },
    "lesson-11": {
      "a01": `
        for n in range(1, 21):
            if n % 15 == 0:
                print("FizzBuzz")
            elif n % 3 == 0:
                print("Fizz")
            elif n % 5 == 0:
                print("Buzz")
            else:
                print(n)
`,
      "a02": `
        def format_score(name, score):
            # TODO: improve the formatting
            return f"{name}: {score}"

        print(format_score("Ada", 7))
        print(format_score("Sam", 12))
`,
    },
    "lesson-12": {
      "a01": `
        n = 1
        for i in range(1, 11):
            n = n * 2
            print(i, n, "digits:", len(str(n)))
`,
      "a02": `
        def draw_arrow(width=6):
            body = "-" * width
            head = ">>"
            print(body + head)

        draw_arrow(6)
`,
    },
    "lesson-13": {
      "a01": `
        import random
        import json

        items = ["red", "blue", "green"]
        choice = random.choice(items)
        data = {"choice": choice}
        print("Choice:", choice)
        print(json.dumps(data))
`,
      "a02": `
        events = ["click", "tick", "tick", "quit"]
        running = True

        for event in events:
            if event == "click":
                print("handle click")
            elif event == "tick":
                print("handle tick")
            elif event == "quit":
                print("handle quit")
                running = False
            if not running:
                break
`,
    },
    "lesson-14": {
      "a01": `
        def move(n, source, target, spare):
            if n == 1:
                print(source, "->", target)
                return
            move(n - 1, source, spare, target)
            print(source, "->", target)
            move(n - 1, spare, target, source)

        move(3, "A", "C", "B")
`,
      "a02": `
        def pattern(n):
            if n == 0:
                return ""
            return pattern(n - 1) + ("*" * n) + "\\n"

        print(pattern(5))
`,
    },
    "lesson-15": {
      "a01": `
        # TODO: add comments to explain why each step exists
        def average(nums):
            total = 0
            for n in nums:
                total += n
            return total / len(nums)

        print(average([2, 4, 6]))
`,
      "a02": `
        # Bug hunt: fix the logic
        score = 7

        if score > 10:
            print("High score")
        else:
            print("Needs work")

        # TODO: adjust the condition to match the requirement
`,
    },
    "lesson-4": {
      "a02": `
          # Starter: run a simple program
          name = "Coder"
          print("Hello", name)

          # TODO: add another print line
          # TODO: write a note to a file
          with open("notes.txt", "w") as f:
              f.write("My first note")
`,
    },
    "lesson-5": {
      "a01": `
        # Four 4s challenge
        # Use exactly four 4s each line
        print(44/4 - 4)  # target 1
        # TODO: add expressions for other targets
`,
      "a02": `
        # Evaluate expressions
        expr1 = (3 + 4) * 2 - 5
        expr2 = 12 / 3 + 4 * 2
        expr3 = 4 * 4 - 4 ** 2
        print(expr1, expr2, expr3)

        # TODO: add your fixed expressions
`,
    },
    "lesson-6": {
      "a01": `
        # Swap two variables
        a = 10
        b = 3
        print("Before:", a, b)

        temp = a
        a = b
        b = temp

        print("After:", a, b)
`,
      "a02": `
        # Replace input() with fixed values for testing
        name = "Ada"
        age = 12
        score = 9.5
        likes_python = True

        print(name, age, score, likes_python)
        print(type(name), type(age), type(score), type(likes_python))
`,
    },
    "lesson-8": {
      "a01": `
        # Reverse a list with a loop
        items = [1, 2, 3, 4]
        reversed_items = []
        for i in range(len(items) - 1, -1, -1):
            reversed_items.append(items[i])
        print(items, "->", reversed_items)
`,
      "a02": `
        sizes = ("small", "medium", "large")
        orders = ["tea", "latte"]
        print("Sizes:", sizes)
        print("Orders:", orders)

        print("First two:", orders[0:2])
        orders.append("hot chocolate")
        orders[0] = "espresso"
        print("Updated:", orders)

        # TODO: try the tuple error
        # sizes.append("xl")
`,
    },
    "lesson-9": {
      "a01": `
        # TODO: adjust the values using the comments
        speed = 3  # adjust speed
        lives = 3  # limit lives
        name = "Ada"  # ask for name

        print("Speed:", speed)
        print("Lives:", lives)
        print("Name:", name)
`,
      "a02": `
        # TODO: refactor names and add why comments
        def total_score(scores):
            total = 0
            for score in scores:
                total += score
            return total

        scores = [5, 3, 2]
        print(total_score(scores))
`,
    },
  };

  function normalizeHintCode(value){
    if(!value) return "";
    let text = String(value).replace(/\r\n/g, "\n");
    text = text.replace(/^\n+/, "").replace(/\n+$/, "");
    const lines = text.split("\n");
    const indents = lines
      .filter(line => line.trim().length)
      .map(line => line.match(/^ */)[0].length);
    const minIndent = indents.length ? Math.min(...indents) : 0;
    if(minIndent > 0){
      return lines.map(line => line.slice(minIndent)).join("\n");
    }
    return lines.join("\n");
  }

  const state = store.get(stateKey, {
    code: DEFAULT_CODE,
    output: null,
    answers: {},
    checked: {},
    notes: {},
    files: []
  });

  let runFiles = [];
  captureHintTemplate();
  initFloatingEditor();
  initHintButton();

  function hintCodeForStep(stepId){
    const library = HINT_LIBRARY[lessonId];
    if(library && library[activityId]){
      const mapped = normalizeHintCode(library[activityId]);
      if(mapped.trim()) return mapped;
    }
    if(hintTemplateText && (!hintTemplateStep || hintTemplateStep === stepId)){
      return hintTemplateText;
    }
    let template = document.querySelector(`template[data-hint-code-template="${stepId}"]`);
    if(!template){
      template = document.querySelector("template[data-hint-code-template]");
    }
    if(template){
      const text = template.textContent || "";
      const normalized = normalizeHintCode(text);
      if(normalized.trim()){
        return normalized;
      }
    }
    console.warn("Hint template not found; using default skeleton.");
    return HINT_DEFAULT_CODE;
  }

  function hintLabelForStep(editorCard, stepId){
    if(editorCard && editorCard.dataset.hintLabel){
      return editorCard.dataset.hintLabel;
    }
    return stepId;
  }

  function recordHintUsed(stepId, label){
    if(!state.hintsUsed || typeof state.hintsUsed !== "object"){
      state.hintsUsed = {};
    }
    state.hintsUsed[stepId] = {
      label: label || stepId,
      used_at: new Date().toISOString()
    };
    saveState();
  }

  function initHintButton(){
    if(!codeEditor || !runBtn) return;
    const runRow = runBtn.closest(".row");
    if(!runRow || runRow.querySelector("[data-hint-code]")) return;
    const editorCard = codeEditor.closest(".card");
    const stepId = (editorCard && editorCard.dataset.hintStep) ? editorCard.dataset.hintStep : (hintTemplateStep || "code-step-1");
    const label = hintLabelForStep(editorCard, stepId);

    const hintBtn = document.createElement("button");
    hintBtn.type = "button";
    hintBtn.className = "btn";
    hintBtn.dataset.hintCode = stepId;
    hintBtn.textContent = "Hint (starter code)";
    hintBtn.addEventListener("click", () => {
      const warning = "This will replace your current code with a starter skeleton. Continue?";
      if(!confirm(warning)) return;
      const hintCode = hintCodeForStep(stepId);
      codeEditor.value = hintCode;
      state.code = hintCode;
      recordHintUsed(stepId, label);
      toast("Hint inserted. Your previous code was replaced.");
    });
    runRow.appendChild(hintBtn);
  }

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

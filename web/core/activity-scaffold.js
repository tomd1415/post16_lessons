(() => {
  const root = document.querySelector("[data-lesson-id][data-activity-id]");
  if (!root || typeof store === "undefined") return;

  const lessonId = root.dataset.lessonId;
  const activityId = root.dataset.activityId;
  const fallbackKey = `tlac_${lessonId}_${activityId}_state`;
  const stateKey = typeof stateKeyFromIds === "function"
    ? (stateKeyFromIds(lessonId, activityId) || fallbackKey)
    : fallbackKey;

  let state = store.get(stateKey, {
    answers: {},
    notes: {},
    checklist: {},
    checked: {}
  });
  if (!state || typeof state !== "object" || Array.isArray(state)) {
    state = { answers: {}, notes: {}, checklist: {}, checked: {} };
  }
  if (!state.answers || typeof state.answers !== "object") state.answers = {};
  if (!state.notes || typeof state.notes !== "object") state.notes = {};
  if (!state.checklist || typeof state.checklist !== "object") state.checklist = {};
  if (!state.checked || typeof state.checked !== "object") state.checked = {};

  const save = () => store.set(stateKey, state);

  function initNotes(){
    root.querySelectorAll("[data-field]").forEach(el => {
      const key = el.dataset.field;
      if (key in state.notes) {
        el.value = state.notes[key];
      }
      el.addEventListener("input", () => {
        state.notes[key] = el.value;
        save();
      });
    });
  }

  function initChecklist(){
    root.querySelectorAll("input[type='checkbox'][data-check]").forEach(box => {
      const key = box.dataset.check;
      if (key in state.checklist) {
        box.checked = !!state.checklist[key];
      }
      box.addEventListener("change", () => {
        state.checklist[key] = box.checked;
        save();
      });
    });
  }

  function initQuizzes(){
    root.querySelectorAll("[data-quiz]").forEach(quiz => {
      const quizId = quiz.dataset.quiz;
      if (!quizId) return;
      const stored = state.answers[quizId];
      if (stored) {
        const input = quiz.querySelector(`input[type='radio'][value="${stored}"]`);
        if (input) input.checked = true;
      }
      quiz.querySelectorAll("input[type='radio']").forEach(input => {
        input.addEventListener("change", () => {
          state.answers[quizId] = input.value;
          save();
        });
      });
    });

    root.querySelectorAll("[data-quiz-check]").forEach(btn => {
      btn.addEventListener("click", () => {
        const quizId = btn.dataset.quizCheck;
        if (!quizId) return;
        const quiz = root.querySelector(`[data-quiz="${quizId}"]`);
        const feedback = root.querySelector(`[data-quiz-feedback="${quizId}"]`);
        if (!quiz || !feedback) return;

        const correct = quiz.dataset.correct;
        const answer = state.answers[quizId];
        if (!answer) {
          feedback.style.display = "";
          feedback.className = "note warn";
          feedback.innerHTML = "<b>Pick an answer first.</b>";
          return;
        }

        const ok = answer === correct;
        state.checked[quizId] = ok;
        save();

        feedback.style.display = "";
        feedback.className = `note ${ok ? "good" : "warn"}`;
        feedback.innerHTML = ok
          ? "<b>Correct.</b> Nice work."
          : "<b>Not quite.</b> Re-read the prompt and try again.";
      });
    });
  }

  initNotes();
  initChecklist();
  initQuizzes();
})();

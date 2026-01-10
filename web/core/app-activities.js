let manifestCachePromise = null;

async function loadLessonManifest(){
  if(manifestCachePromise) return manifestCachePromise;
  manifestCachePromise = (async ()=>{
    try{
      const res = await fetch("/lessons/manifest.json", { credentials: "same-origin" });
      if(!res.ok) return null;
      return await res.json();
    }catch{
      return null;
    }
  })();
  return manifestCachePromise;
}

function parseActivityIds(){
  const rooted = document.querySelector("[data-lesson-id][data-activity-id]");
  if(rooted){
    const lid = rooted.dataset.lessonId;
    const aid = rooted.dataset.activityId;
    if(lid && aid) return { lessonId: lid, activityId: aid };
  }

  const match = /\/lessons\/(lesson-\d+)\/activities\/(\d+)/.exec(window.location.pathname || "");
  if(match){
    const num = match[2].padStart(2, "0");
    return { lessonId: match[1], activityId: `a${num}` };
  }
  return null;
}

function firstContainer(){
  const containers = $$(".container");
  const main = containers.find(c => !c.closest(".topbar"));
  return main || document.body;
}

function insertBrief(card){
  const host = firstContainer();
  const heading = host.querySelector("h1");
  if(heading && heading.parentElement === host){
    heading.insertAdjacentElement("afterend", card);
    return;
  }
  host.insertBefore(card, host.firstChild);
}

function evidenceText(activity){
  const raw = activity && activity.expectedEvidence;
  if(typeof raw === "string" && raw.trim()) return raw.trim();
  return "Complete every interactive block on this page and save/export your work when prompted.";
}

function actionStepsHtml(){
  const steps = [
    "Read the on-page instructions below the title—no booklet needed.",
    "Work through every card/section in order. When you see buttons like Check, Reset, Export, or Save, use them before moving on.",
    "Fill any text areas or notes so your thinking is captured on this page.",
    "If there is a quiz, choose answers for all questions, then press Check to see feedback.",
    "If there is an Export/Download button, click it to save your evidence locally or share it with your teacher as directed."
  ];
  return `<ol class="list">${steps.map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol>`;
}

function objectivesList(lesson, activity){
  const ids = activity && Array.isArray(activity.objectiveIds) ? activity.objectiveIds : [];
  const lookup = (lesson && Array.isArray(lesson.objectives)) ? lesson.objectives : [];
  return ids
    .map(id => lookup.find(o => o.id === id))
    .filter(Boolean)
    .map(o => o.text);
}

function buildBriefHtml(lesson, activity){
  const objectives = objectivesList(lesson, activity);
  const summary = lesson && lesson.summary ? escapeHtml(lesson.summary) : "";
  const evidence = escapeHtml(evidenceText(activity));
  const lessonTitle = lesson && lesson.title ? escapeHtml(lesson.title) : "";
  const activityTitle = activity && activity.title ? escapeHtml(activity.title) : "";

  const objectivesHtml = objectives.length
    ? `<ul class="list">${objectives.map(text => `<li>${escapeHtml(text)}</li>`).join("")}</ul>`
    : "<p><small>Learning goals load automatically when available.</small></p>";

  const contextHtml = summary
    ? `<p><b>Lesson context</b><br>${summary}</p>`
    : "";

  return `
    <details class="brief">
      <summary>Task brief</summary>
      <div class="brief-body">
        <div>
          <p><small>${lessonTitle}</small></p>
          <p><b>${activityTitle || "This activity"}</b></p>
          ${contextHtml}
          <p><b>What to do</b><br>${evidence}</p>
          <p><b>How to complete this page</b></p>
          ${actionStepsHtml()}
        </div>
        <div>
          <p><b>Learning goals</b></p>
          ${objectivesHtml}
          <p><small>Everything needed is on this page; you do not need the printed booklet to complete it.</small></p>
        </div>
      </div>
    </details>
  `;
}

async function initActivityBrief(){
  if(!/\/activities\//.test(window.location.pathname || "")) return;
  const ids = parseActivityIds();
  if(!ids) return;
  const manifest = await loadLessonManifest();
  if(!manifest || !Array.isArray(manifest.lessons)) return;
  const lesson = manifest.lessons.find(l => l.id === ids.lessonId);
  if(!lesson || !Array.isArray(lesson.activities)) return;
  const activity = lesson.activities.find(a => a.id === ids.activityId);
  if(!activity) return;

  const card = document.createElement("div");
  card.className = "card task-brief";
  card.innerHTML = buildBriefHtml(lesson, activity);
  insertBrief(card);
}

let howToMapPromise = null;

async function loadHowToMap(){
  if(howToMapPromise) return howToMapPromise;
  howToMapPromise = (async ()=>{
    try{
      const res = await fetch("/core/howto-map.json", { credentials: "same-origin" });
      if(!res.ok) return {};
      return await res.json();
    }catch{
      return {};
    }
  })();
  return howToMapPromise;
}

function buildHowToHtml(steps){
  if(!steps || !steps.length) return "";
  return `
    <div class="card howto">
      <h2>How to complete this activity</h2>
      <ol class="list">
        ${steps.map(s => `<li>${escapeHtml(s)}</li>`).join("")}
      </ol>
    </div>
  `;
}

function insertHowTo(card){
  const host = firstContainer();
  const brief = host.querySelector(".task-brief");
  if(brief){
    brief.insertAdjacentElement("afterend", card);
    return;
  }
  const h1 = host.querySelector("h1");
  if(h1){
    h1.insertAdjacentElement("afterend", card);
    return;
  }
  host.insertBefore(card, host.firstChild);
}

function resolveHowToSteps(ids, map){
  if(!ids || !map) return null;
  const byLesson = map[ids.lessonId];
  if(!byLesson) return null;
  return byLesson[ids.activityId] || null;
}

async function initActivityHowTo(){
  if(!/\/activities\//.test(window.location.pathname || "")) return;
  const ids = parseActivityIds();
  const map = await loadHowToMap();
  const steps = resolveHowToSteps(ids, map);
  if(!steps || !steps.length) return;
  const html = buildHowToHtml(steps);
  const wrapper = document.createElement("div");
  wrapper.innerHTML = html;
  const card = wrapper.firstElementChild;
  if(!card) return;
  insertHowTo(card);
}

export { initActivityBrief, initActivityHowTo };

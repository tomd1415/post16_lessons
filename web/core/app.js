
/* Minimal helpers (offline-friendly) */
const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

const store = {
  get(key, fallback=null){
    try{ const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; }catch{ return fallback; }
  },
  set(key, value, opts={}){
    try{ localStorage.setItem(key, JSON.stringify(value)); }catch{}
    if(opts && opts.skipSync) return;
    if(window.tlacSync && typeof window.tlacSync.queue === "function"){
      window.tlacSync.queue(key, value);
    }
  },
  del(key){ try{ localStorage.removeItem(key); }catch{} }
};

const ROLE_MENUS = {
  pupil: {
    label: "Pupil",
    items: [
      { label: "Student hub", href: "/index.html" },
      { label: "Course catalogue", href: "/index.html#catalog" },
      { label: "Lesson 1 student hub", href: "/lessons/lesson-1/student.html" }
    ]
  },
  teacher: {
    label: "Teacher",
    items: [
      { label: "Teacher hub", href: "/teacher.html" },
      { label: "Teacher view", href: "/teacher-view.html" },
      { label: "Teacher stats", href: "/teacher-stats.html" },
      { label: "Revision history", href: "/teacher-history.html" },
      { label: "Link registry", href: "/teacher-links.html" },
      { label: "Lesson 1 teacher hub", href: "/lessons/lesson-1/index.html" },
      { label: "Lesson 1 lesson plan", href: "/lessons/lesson-1/teacher/lesson-plan.html" },
      { label: "Lesson 1 print cards", href: "/lessons/lesson-1/teacher/print-cards.html" },
      { label: "Lesson 1 answer key", href: "/lessons/lesson-1/teacher/answer-key.html" },
      { label: "Student hub", href: "/index.html" }
    ]
  },
  admin: {
    label: "Admin",
    items: [
      { label: "Admin hub", href: "/admin.html" },
      { label: "Audit log", href: "/admin-audit.html" },
      { label: "Create user", href: "/admin.html#admin-create-user" },
      { label: "Import CSV", href: "/admin.html#admin-import" },
      { label: "Teacher view", href: "/teacher-view.html" },
      { label: "Teacher stats", href: "/teacher-stats.html" },
      { label: "Revision history", href: "/teacher-history.html" },
      { label: "Link registry", href: "/teacher-links.html" },
      { label: "Teacher hub", href: "/teacher.html" },
      { label: "Student hub", href: "/index.html" }
    ]
  }
};

const SYNC_PENDING_KEY = "tlac_sync_pending";
const SYNC_META_PREFIX = "tlac_meta_";
const SYNC_DEBOUNCE_MS = 1200;
const syncTimers = {};

function readPending(){
  try{ return JSON.parse(localStorage.getItem(SYNC_PENDING_KEY) || "{}"); }catch{ return {}; }
}

function writePending(pending){
  try{ localStorage.setItem(SYNC_PENDING_KEY, JSON.stringify(pending || {})); }catch{}
}

function metaKeyForState(stateKey){
  return `${SYNC_META_PREFIX}${stateKey}`;
}

function readMeta(stateKey){
  try{ return JSON.parse(localStorage.getItem(metaKeyForState(stateKey)) || "null"); }catch{ return null; }
}

function writeMeta(stateKey, meta){
  try{ localStorage.setItem(metaKeyForState(stateKey), JSON.stringify(meta || {})); }catch{}
}

function parseStateKey(stateKey){
  const match = /^tlac_l(\d+)_([a]\d+)_state$/.exec(stateKey || "");
  if(!match) return null;
  return {
    lesson_id: `lesson-${match[1]}`,
    activity_id: match[2]
  };
}

function stateKeyFromIds(lessonId, activityId){
  const match = /^lesson-(\d+)$/.exec(lessonId || "");
  if(!match || !activityId) return null;
  return `tlac_l${match[1]}_${activityId}_state`;
}

function toast(msg){
  const el = $("#toast");
  if(!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(()=> el.classList.remove("show"), 2400);
}

function readStoredRole(){
  try{
    const raw = localStorage.getItem("tlac_role");
    if(!raw) return null;
    try{ return JSON.parse(raw); }catch{ return raw; }
  }catch{
    return null;
  }
}

function escapeHtml(s){
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function tryParseJsonString(value){
  if(typeof value !== "string") return null;
  const trimmed = value.trim();
  if(!trimmed) return null;
  const looksJson =
    (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"));
  if(!looksJson) return null;
  try{
    return JSON.parse(trimmed);
  }catch{
    return null;
  }
}

function renderStateNode(value, seen){
  const parsed = tryParseJsonString(value);
  if(parsed !== null) return renderStateNode(parsed, seen);

  if(value === null || value === undefined){
    return "<span class=\"state-null\">None</span>";
  }
  if(value && typeof value === "object"){
    if(!seen){
      seen = new WeakSet();
    }
    if(seen.has(value)){
      return "<span class=\"state-null\">[Circular]</span>";
    }
    seen.add(value);
  }
  if(typeof value === "string"){
    return `<span class="state-text">${escapeHtml(value)}</span>`;
  }
  if(typeof value === "number"){
    return `<span class="state-text">${value}</span>`;
  }
  if(typeof value === "boolean"){
    return `<span class="state-text">${value ? "Yes" : "No"}</span>`;
  }
  if(Array.isArray(value)){
    if(!value.length){
      return "<span class=\"state-null\">Empty list</span>";
    }
    return `<ol class="state-list">${value.map(item => `<li>${renderStateNode(item, seen)}</li>`).join("")}</ol>`;
  }
  if(typeof value === "object"){
    const entries = Object.entries(value || {});
    if(!entries.length){
      return "<span class=\"state-null\">No fields</span>";
    }
    return `<dl class="state-dl">${entries
      .map(([key, val]) => (
        `<div class="state-row"><dt>${escapeHtml(key)}</dt><dd>${renderStateNode(val, seen)}</dd></div>`
      ))
      .join("")}</dl>`;
  }
  return `<span class="state-text">${escapeHtml(String(value))}</span>`;
}

function renderStateReadable(value){
  if(value === null || value === undefined || value === ""){
    return "";
  }
  return `<div class="state-view">${renderStateNode(value, null)}</div>`;
}

function roleToMenu(role){
  if(role === "admin") return "admin";
  if(role === "teacher") return "teacher";
  return "pupil";
}

function preferredMenuFromPath(){
  const path = window.location.pathname || "";
  if(path.startsWith("/admin")) return "admin";
  if(path.startsWith("/teacher")) return "teacher";
  if(path.includes("/teacher/")) return "teacher";
  if(path.includes("/activities/")) return "pupil";
  if(path.endsWith("/student.html")) return "pupil";
  if(/\/lessons\/lesson-\d+\/index\.html$/.test(path)) return "teacher";
  if(/\/lessons\/lesson-\d+\/?$/.test(path)) return "teacher";
  return "pupil";
}

let roleMenuHost = null;

function renderRoleMenu(menuKey){
  if(!roleMenuHost) return;
  const menu = ROLE_MENUS[menuKey] || ROLE_MENUS.pupil;
  const items = menu.items
    .map(item => `<li><a href="${escapeHtml(item.href)}">${escapeHtml(item.label)}</a></li>`)
    .join("");
  roleMenuHost.innerHTML = `
    <details class="role-menu">
      <summary>
        <span class="menu-label">Menu</span>
        <span class="tag">${escapeHtml(menu.label)}</span>
      </summary>
      <nav aria-label="${escapeHtml(menu.label)} menu">
        <ul class="list menu-items">
          ${items}
        </ul>
      </nav>
    </details>
  `;
}

function initRoleMenu(){
  const container = $(".topbar .container");
  if(!container) return;
  let row = container.querySelector(".row");
  if(!row){
    row = document.createElement("div");
    row.className = "row";
    container.appendChild(row);
  }
  roleMenuHost = row.querySelector("#roleMenu");
  if(!roleMenuHost){
    roleMenuHost = document.createElement("div");
    roleMenuHost.id = "roleMenu";
    row.appendChild(roleMenuHost);
  }
  const stored = readStoredRole();
  const menuKey = stored ? roleToMenu(stored) : preferredMenuFromPath();
  renderRoleMenu(menuKey);
}

function updateRoleMenu(role){
  if(!roleMenuHost) return;
  const menuKey = role ? roleToMenu(role) : preferredMenuFromPath();
  renderRoleMenu(menuKey);
}

function applyTeacherMode(on){
  document.documentElement.dataset.teacher = on ? "1" : "0";
  $$(".teacher-only").forEach(e => e.style.display = on ? "" : "none");
}

function isStaffRole(role){
  return role === "teacher" || role === "admin";
}

function findTeacherHubLinks(){
  return $$("a").filter(link => {
    const text = (link.textContent || "").toLowerCase();
    if(text.includes("teacher hub")) return true;
    const href = (link.getAttribute("href") || "").toLowerCase();
    return href.includes("teacher.html");
  });
}

function syncTeacherHubLinks(role){
  const show = isStaffRole(role);
  findTeacherHubLinks().forEach(link => {
    link.style.display = show ? "" : "none";
    link.setAttribute("aria-hidden", show ? "false" : "true");
  });
}

let authCache;
async function getAuthInfo(){
  if(window.tlacAuthReady){
    try{
      const data = await window.tlacAuthReady;
      return data || null;
    }catch{}
  }

  if(authCache !== undefined) return authCache;
  try{
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    if(res.ok){
      authCache = await res.json();
      return authCache;
    }
  }catch{}
  authCache = null;
  return authCache;
}

async function flushPending(){
  if(!navigator.onLine) return;
  const pending = readPending();
  const keys = Object.keys(pending);
  if(!keys.length) return;

  const auth = await getAuthInfo();
  if(!auth || !auth.csrf_token) return;

  for(const stateKey of keys){
    const entry = pending[stateKey];
    if(!entry || !entry.lesson_id || !entry.activity_id) continue;
    try{
      const res = await fetch(`/api/activity/state/${entry.lesson_id}/${entry.activity_id}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": auth.csrf_token
        },
        credentials: "same-origin",
        body: JSON.stringify({
          state: entry.state,
          client_saved_at: entry.client_saved_at
        })
      });
      if(!res.ok) continue;
      const data = await res.json().catch(()=> ({}));
      if(data.updated_at){
        writeMeta(stateKey, { updated_at: data.updated_at });
      }
      delete pending[stateKey];
      writePending(pending);
    }catch{}
  }
}

async function bootstrapServerState(){
  const auth = await getAuthInfo();
  if(!auth) return;
  try{
    const res = await fetch("/api/activity/state", { credentials: "same-origin" });
    if(!res.ok) return;
    const data = await res.json();
    const items = Array.isArray(data.items) ? data.items : [];
    const pending = readPending();
    for(const item of items){
      const stateKey = stateKeyFromIds(item.lesson_id, item.activity_id);
      if(!stateKey) continue;
      if(pending[stateKey]) continue;
      const meta = readMeta(stateKey);
      const localStamp = meta && meta.updated_at ? Date.parse(meta.updated_at) : 0;
      const remoteStamp = item.updated_at ? Date.parse(item.updated_at) : 0;
      if(localStamp && remoteStamp && remoteStamp <= localStamp) continue;
      store.set(stateKey, item.state, { skipSync: true });
      if(item.updated_at){
        writeMeta(stateKey, { updated_at: item.updated_at });
      }
    }
  }catch{}
}

window.tlacSync = {
  queue(stateKey, state){
    const ids = parseStateKey(stateKey);
    if(!ids) return;
    const pending = readPending();
    pending[stateKey] = {
      lesson_id: ids.lesson_id,
      activity_id: ids.activity_id,
      state,
      client_saved_at: new Date().toISOString()
    };
    writePending(pending);
    clearTimeout(syncTimers[stateKey]);
    syncTimers[stateKey] = setTimeout(()=>{ flushPending(); }, SYNC_DEBOUNCE_MS);
  },
  flush: flushPending,
  hydrate: bootstrapServerState
};

window.tlacReady = (async ()=>{
  await bootstrapServerState();
  await flushPending();
})();

window.addEventListener("online", ()=>{ flushPending(); });

function getTeacherMode(role){
  const resolved = role || document.documentElement.dataset.role;
  if(!isStaffRole(resolved)) return false;
  const params = new URLSearchParams(location.search);
  if(params.get("teacher")==="1") return true;
  return store.get("tlac_teacher_mode", false);
}

function setTeacherMode(on, opts={}){
  const persist = opts.persist !== false;
  if(persist) store.set("tlac_teacher_mode", !!on);
  applyTeacherMode(!!on);
}

async function resolveRole(){
  const existing = document.documentElement.dataset.role;
  if(existing) return existing;

  if(window.tlacAuthReady){
    try{
      const data = await window.tlacAuthReady;
      if(data && data.user && data.user.role){
        try{ localStorage.setItem("tlac_role", JSON.stringify(data.user.role)); }catch{}
        document.documentElement.dataset.role = data.user.role;
        return data.user.role;
      }
    }catch{}
  }

  try{
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    if(res.ok){
      const data = await res.json();
      if(data && data.user && data.user.role){
        try{ localStorage.setItem("tlac_role", JSON.stringify(data.user.role)); }catch{}
        document.documentElement.dataset.role = data.user.role;
        return data.user.role;
      }
    }
  }catch{}

  const stored = readStoredRole();
  if(stored === "pupil"){
    document.documentElement.dataset.role = stored;
    return stored;
  }

  return null;
}

async function initTeacherToggle(){
  const btn = $("#teacherToggle");
  if(btn) btn.style.display = "none";
  setTeacherMode(false, { persist: false });
  syncTeacherHubLinks(null);
  const role = await resolveRole();
  syncTeacherHubLinks(role);
  updateRoleMenu(role);
  const on = getTeacherMode(role);

  if(!isStaffRole(role)){
    setTeacherMode(false);
    if(btn) btn.style.display = "none";
    return;
  }

  setTeacherMode(on);
  if(!btn) return;
  btn.style.display = "";
  btn.textContent = on ? "Teacher mode: ON" : "Teacher mode: OFF";
  btn.addEventListener("click", ()=>{
    const now = !getTeacherMode(role);
    setTeacherMode(now);
    btn.textContent = now ? "Teacher mode: ON" : "Teacher mode: OFF";
    toast(now ? "Teacher mode enabled" : "Teacher mode disabled");
  });
}

function shuffle(arr){
  const a = arr.slice();
  for(let i=a.length-1;i>0;i--){
    const j = Math.floor(Math.random()*(i+1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function uid(){
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

function downloadText(filename, text, mime="text/plain"){
  const blob = new Blob([text], {type: mime});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function printPage(){
  window.print();
}

document.addEventListener("DOMContentLoaded", ()=>{
  initRoleMenu();
  initTeacherToggle();
  initActivityBrief();
  initActivityHowTo();
});

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

const HOW_TO_MAP = {
  "lesson-1": {
    a01: [
      "Pick a device card from the left column (it highlights when selected).",
      "Click a bin’s “Place here” button (Computer / Not a computer / Depends) to drop the selected card.",
      "If you change your mind, use Move to reselect the card, then place it in a different bin or Remove to take it out.",
      "Read the prompts and add a reflection in the text box.",
      "Click Export to download your placements and notes; Reset clears everything to start again."
    ],
    a02: [
      "Click a term button, then click the definition you think matches it. Each pair is stored immediately.",
      "Check the Your matches table to see your current pairs; matched items turn into a table row.",
      "Press Check score to see how many pairs are correct; the score updates after every check.",
      "Toggle Flashcards to study terms and definitions together if you need a hint.",
      "Use Reset to clear all matches and try again; Export is not needed for this activity."
    ],
    a03: [
      "Fill Team name, Spokesperson, and Robo‑chef speciality so your export is labelled.",
      "In the Function tree, click Add top-level function to create the first major task (e.g., Prep ingredients).",
      "For any function, click Add sub-task to break it down; choose a type: action, sensing/check, or reusable.",
      "Edit lets you rename or retype a node; Delete removes a node and its children (not the root). Aim for at least one branch that is 3 levels deep.",
      "Export to JSON or Print when done; Reset clears all entries." 
    ],
    a04: [
      "For each recipe card, tick the steps you think belong in a general pattern (steps that repeat across recipes).",
      "The Common steps list shows steps that appear in every recipe automatically.",
      "Give your pattern a name and note what varies (e.g., temperature, time, ingredients).",
      "Review the Reusable template at the bottom; it rebuilds using the steps you selected."
      ,"Export or Print to keep your work; Reset clears selections."
    ],
    a05: [
      "Open each scenario card and read the question about what to keep/ignore.",
      "Tick the checkboxes for details you would keep because they change the outcome or safety.",
      "Click Check on each card to see feedback; adjust your ticks and re-check if needed.",
      "Teacher mode reveals the explanation text; pupils just see scores.",
      "Use Export to save your choices; Reset clears all selections."
    ],
    a06: [
      "Pick a mode: Line (easy) or Circle (harder). Click Generate new class any time to reshuffle heights.",
      "Line mode: use ↑/↓ buttons to reorder students shortest → tallest. Press Check to verify; Auto sort shows the correct order.",
      "Circle mode: use ←/→ to move students around the circle; watch the Total neighbour difference score drop. Try the heuristic to see an automatic attempt; Shuffle to change the order.",
      "Use Export to download your final arrangements; Reset wipes and reloads the page state."
    ],
    a07: [
      "Choose a big problem from the dropdown and read the starter text.",
      "Click Add sub-problem for each component you identify; enter a short title, detail, and mark it as software or non-software.",
      "Add several items and make sure at least one is a concrete software idea (real data, real outputs).",
      "Click Check requirement to confirm you have at least one software idea; adjust if you get a warning.",
      "Use Export to save, Reset to start over. The examples list is for backup only if you get stuck."
    ],
    a08: [
      "For each multiple-choice question, select one option (a dot appears when chosen).",
      "For short-answer questions, type your response in the text area in your own words.",
      "Click Submit to see your MCQ score and a result table. Short answers are not auto-marked; review them with a teacher.",
      "Print if you need a paper copy for checking. Reset clears all answers so you can retake."
    ]
  },
  "lesson-2": {
    a01: [
      "Answer the three quick-check questions using the radio buttons, then press Check for each to see feedback.",
      "In Step 2, fill the three short lines: define formal language, give one formal example, and one natural example.",
      "Task A: For each statement, pick Formal or Natural. Aim for clear, unambiguous wording.",
      "Task B: Rewrite the hot chocolate instruction as numbered, precise steps with no vague words.",
      "Task C: Swap with a partner (or self-review), mark unclear wording, rewrite one step, tick the checklist, and summarise in the notes box.",
      "Fill the final reflection box about what you improved; use Reset only if you need a fresh start." 
    ],
    a02: [
      "Answer the three quick checks on source vs machine code and click Check for feedback.",
      "Fill Step 2 with one short example of source code and one of machine code.",
      "Task A: Mark each statement S (source) or M (machine).",
      "Task B: Pick the missing pipeline step, click Check, and write why that step is needed.",
      "Task C: Complete the translation sentence for x = 2 + 3 and (optional) note an opcode; tick the checklist items when covered.",
      "Write a short reflection on where errors can happen in translation; Export/Print if you need to keep your answers." 
    ],
    a03: [
      "Do the three quick checks about phase order, testing timing, and enhancement; click Check on each.",
      "Fill Step 2 with one short line describing what happens in each phase (analysis, design, programming, testing, enhancement).",
      "Task A: Assign an order number 1–5 to every phase (no blanks).",
      "Task B: Choose the matching artefact/output for each phase (requirements, wireframe, code, test report, change log).",
      "Task C: For the focus timer mini-case, add one concrete action per phase. Tick the checklist when goal/inputs/steps/test are covered.",
      "Add a reflection on which phase is most important and where bugs creep in; Export/Print if required." 
    ],
    a04: [
      "Answer the three quick checks (spec quality, functional vs non-functional, example). Click Check for each.",
      "Fill Step 2 with one functional and one non-functional example in your own words.",
      "Task A: Choose a simple game idea (write a short title).",
      "Task B: Fill the spec table: goal, inputs, outputs, rules, constraints. Keep each as one clear line.",
      "Task C: Write three testable acceptance statements (“The game should…”). Add an accessibility constraint in the stretch if you can.",
      "Tick the checklist, then add a reflection on the hardest requirement to test; Export/Print if you need to submit." 
    ]
  },
  "lesson-3": {
    a01: [
      "Answer the three quick checks on decision symbol, sequence, and pseudocode; press Check on each to reveal feedback.",
      "Fill Step 2 with your own definitions for sequence/decision and note the hardest symbol.",
      "Task A: Pick a daily routine and write 5 short steps; tick Decision? where a branch happens.",
      "Task B: Add one IF condition and complete both Yes and No paths in the table.",
      "Task C: Use the checklist to plan your flowchart: Start/End ovals, rectangles for actions, diamonds for decisions with Yes/No labels, arrows/loops with exits.",
      "Write the structured notes and a brief reflection on decisions/loops; Export/Print if you need a copy." 
    ],
    a02: [
      "Answer the three quick checks (IO symbol, what input means, output example) and click Check for each.",
      "Fill the quick IO table for camera, washing machine, and microwave (one input/output each).",
      "Task A: Choose two devices; list at least two inputs and two outputs for each (include sensors, lights, sounds).",
      "Task B: Plan a snippet: write the input trigger, any decision, and the output action; tick IO parallelogram added when you draw it in your flowchart/sketch.",
      "Task C: Tick the completeness checks (path starts with input, ends with output, test idea written).",
      "Finish with a reflection on hidden IO or clarity; Export/Print if needed." 
    ],
    a03: [
      "Answer the quick checks (decision symbol, input/output meaning, loop awareness) and click Check on each.",
      "Fill the machine/IO table: list inputs and outputs for the given machine scenario.",
      "Add flowchart elements: start/end, processes, decisions, IO symbols; note any loop and how it exits.",
      "If pseudocode is offered, rewrite the flow in short numbered steps to match your chart.",
      "Tick the checklist when you have inputs, outputs, steps, and a test. Export/Print to keep your plan; Reset only if restarting." 
    ]
  },
  "lesson-4": {
    a01: [
      "Complete the three quick checks about file extension, running, and saving; press Check for each.",
      "Fill Step 2 with the file name, what should happen when Run is clicked, and one control key.",
      "Task A: Locate the starter file aliens.py, open it, and note the file path; tick the checkboxes.",
      "Task B: Run the game once; record whether it ran and what output or error appeared.",
      "Task C: Make one small edit (caption, speed, lives), run again, and log whether it worked; tick evidence boxes for saved file, screenshot, and notes.",
      "Add a short reflection on what was easy or any error you fixed; Export/Print if you need to submit."
    ],
    a02: [
      "Answer the three quick checks (print, comment symbol, input) and click Check for each.",
      "Read the example code, then in Step 2 edit the code in the editor; use Run code to execute and Save files to keep outputs.",
      "In Plan your run, fill test input, expected output, and the change you will test before pressing Run code.",
      "Use the Run log table to record what changed on each run and whether output was OK or errors occurred.",
      "Review Stdout/Stderr after each run; save any generated files you need as evidence.",
      "Write a reflection on what you changed and what worked; Reset only if you need a clean slate." 
    ]
  },
  "lesson-5": {
    a01: [
      "Review the prompt/goal, then for each target number fill an expression using exactly four 4s and the allowed operators.",
      "Use parentheses to control order; check the operator checklist as you employ each one.",
      "Test tricky expressions in the runner (if available) or evaluate mentally; adjust until the target matches.",
      "Add a short reflection on which targets were hardest and which operators helped most; export/print if needed."
    ],
    a02: [
      "Work through the given expressions: rewrite them with correct parentheses so they evaluate as intended.",
      "Show the working/evaluation steps (what gets computed first) in the provided boxes or notes.",
      "Optionally run your corrected expressions in the runner to confirm outputs match your prediction.",
      "Complete the checklist and add a brief note on common mistakes with precedence; export/print if required." 
    ]
  },
  "lesson-6": {
    a01: [
      "Follow the swap scenario: note starting values, then order the swap steps correctly (including a temp variable).",
      "Fill the value-tracking table after each step to prove the swap works.",
      "Write the final Python swap snippet and run it in the runner; record the output/proof it worked.",
      "Check the checklist items (init, assign, test) and add a short reflection on why the temp is needed." 
    ],
    a02: [
      "Plan your prompts: list what inputs you will ask the user and what types you expect (string/int/float/bool).",
      "Write code to collect input with input(), convert to the right type (int/float/bool), and print a confirmation line.",
      "Run the code in the runner with at least two test inputs; note the outputs and any errors.",
      "Tick the checklist for input, conversion, and output; reflect on where type errors appeared." 
    ]
  },
  "lesson-7": {
    a01: [
      "Read the AND/OR/NOT examples; craft three search strings using the required operators for given scenarios.",
      "Record which results/links you find and note how the operator changed the results.",
      "Map each operator to its effect (narrows/widens/excludes) in the provided table or notes.",
      "Add a short reflection on which operator combination was most useful." 
    ],
    a02: [
      "List the washing machine inputs (sensors/buttons) and outputs (actions) in the table.",
      "Write Boolean rules using AND/OR/NOT to control heater, motor, and door lock (or given components).",
      "Add troubleshooting logic: what should happen if a condition fails (e.g., door open, water low).",
      "Reflect on how the logic prevents unsafe states; export/print if required." 
    ]
  },
  "lesson-8": {
    a01: [
      "Choose a method to reverse a list (slicing, loop, built-in) and write the steps in order.",
      "Create a few test lists and predict the reversed output before running.",
      "Run your reversal in the runner, record outputs, and adjust if a test fails.",
      "Note which method you used and why; tick evidence/checklist items." 
    ],
    a02: [
      "Complete the toolkit examples: create tuples and lists, practice indexing, slicing, append/extend, and unpacking.",
      "Run each snippet in the runner and capture the printed results as evidence.",
      "Try one custom example combining list + tuple operations (e.g., tuple to list, modify, back to tuple).",
      "Summarise what each operation does and any surprises; mark the checklist." 
    ]
  },
  "lesson-9": {
    a01: [
      "Read the provided code/comments; decide what each comment is trying to convey (purpose, warning, todo).",
      "Mark whether each comment is clear or needs improvement; rewrite unclear ones in the notes box.",
      "Run the snippet if present to see behaviour and ensure comments match the code.",
      "Tick the checklist for indentation, naming, and commenting; add a brief reflection on good vs bad comments." 
    ],
    a02: [
      "Inspect the starter code; list quick refactors (better names, smaller functions, clearer comments).",
      "Apply those changes in the editor, then run to confirm behaviour still matches the original intent.",
      "Document before/after for at least one function or block, noting why each change improves readability.",
      "Complete the checklist and add a reflection on which change helped most; export/print if needed." 
    ]
  },
  "lesson-10": {
    a01: [
      "Fill the logic table for the age-checker (conditions and outcomes).",
      "Write the ordered IF/ELSE steps as pseudocode, then convert to Python-style syntax in the notes/editor if provided.",
      "Test the logic with several ages (boundary values) and record outputs; fix any misplaced conditions.",
      "Tick the checklist and note how you tested the branches." 
    ],
    a02: [
      "List inputs (e.g., light colour, pedestrian button) and desired outputs (go/stop signals).",
      "Write the IF/ELSE rules for the traffic light, including safety constraints (e.g., never both green).",
      "Test the rules against sample states; record any conflicts and adjust conditions or order.",
      "Summarise the final rule set and how you would test it in code or a flowchart." 
    ]
  },
  "lesson-11": {
    a01: [
      "Write a function header with clear parameters; state what it should return.",
      "Add at least two test calls with expected outputs; run or mentally check them.",
      "Refine the body to handle edge cases; note any assumptions in the notes box.",
      "Tick the checklist and add a brief reflection on why functions help reuse." 
    ],
    a02: [
      "Practice defining and calling functions with positional and optional parameters as prompted.",
      "Record expected vs actual outputs for each call; adjust default values if outputs are wrong.",
      "Add one custom helper function of your own and test it with two inputs.",
      "Summarise what changed when you altered parameters or defaults." 
    ]
  },
  "lesson-12": {
    a01: [
      "Convert each loop description into a working for/while loop as directed on the page.",
      "Trace one iteration by hand (values per step) to confirm the loop stops correctly.",
      "Run or reason through a boundary case (empty list or zero count) and note the outcome.",
      "Tick the checklist and add a reflection on where loops can get stuck." 
    ],
    a02: [
      "Rewrite repetitive code into a loop; note the variable that changes each pass.",
      "Add a condition to break/continue as required by the prompt and test it with two scenarios.",
      "Record outputs and confirm the loop covers all items without infinite looping.",
      "Summarise one improvement from using the loop." 
    ]
  },
  "lesson-13": {
    a01: [
      "Use the Pygame drawing panel/prompts to create shapes; note which functions you used (draw.line, draw.circle, etc.).",
      "Change at least one parameter (colour, thickness, coords) and observe the effect; record before/after.",
      "Save or export your canvas if the page allows; otherwise screenshot as evidence.",
      "Reflect on which draw calls are reusable for other scenes." 
    ],
    a02: [
      "Follow the music/sound task: load a file as instructed, play/stop it, and tweak volume or loop settings.",
      "Test start/stop behaviour and note any errors (missing file, format).",
      "Record the parameter changes you tried and their effects.",
      "Add a brief reflection on how you would trigger sounds from game events." 
    ],
    a03: [
      "Inspect the event-handling examples; map each event (key/mouse) to an action in the table provided.",
      "Add or edit one handler to change behaviour; test it and note the output or effect.",
      "Check for a quit/close handler and ensure it works; record evidence.",
      "Reflect on how events connect to game loops." 
    ]
  },
  "lesson-14": {
    a01: [
      "Step through the recursion visualiser/drawing task; note the base case and the recursive call.",
      "Change one parameter (depth/angle) and observe the new pattern; record what changed.",
      "Explain in one sentence how the recursion stops; tick the checklist when base/recursive parts are clear.",
      "Capture a screenshot/export of your recursive drawing if available." 
    ],
    a02: [
      "Follow the recursion explanation: trace the given algorithm with a small input and log each call/return.",
      "Identify the base case and the work done before/after the recursive call.",
      "Try a second input to confirm the call stack pattern; note any risk of infinite recursion.",
      "Summarise how you would test or visualise the recursion in code." 
    ],
    a03: [
      "Work through the search/tree task (e.g., alpha-beta); note the prune/keep decisions on each step.",
      "Fill any provided tables for node values and pruned branches.",
      "Explain in a sentence why a branch was cut; add at least one test case of your own.",
      "Reflect on how pruning speeds up search." 
    ]
  },
  "lesson-15": {
    a01: [
      "Read the software spec samples; list what makes a spec well-defined (measurable, unambiguous).",
      "Annotate the provided spec or code snippets with clearer names/comments as directed.",
      "Write one short improvement for scope, acceptance criteria, or stakeholder note.",
      "Summarise the biggest risk if the spec stays vague." 
    ],
    a02: [
      "Review the cartoon/project stages; map each panel to a real software activity (analysis, design, build, test, deploy).",
      "List one failure mode per stage and a mitigation.",
      "Tick checklist items once every stage has a clear activity and risk.",
      "Add a reflection on which stage most often slips and how to prevent it." 
    ],
    a03: [
      "Open the Python programs list; choose a snippet and annotate it with comments explaining purpose and tricky lines.",
      "Run or mentally execute the code to ensure comments match behaviour.",
      "Add one small refactor if allowed (rename variable, extract function) and note the effect.",
      "Save/export your annotated version or notes as evidence." 
    ]
  }
};

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

function resolveHowToSteps(ids){
  if(!ids) return null;
  const byLesson = HOW_TO_MAP[ids.lessonId];
  if(!byLesson) return null;
  return byLesson[ids.activityId] || null;
}

async function initActivityHowTo(){
  if(!/\/activities\//.test(window.location.pathname || "")) return;
  const ids = parseActivityIds();
  const steps = resolveHowToSteps(ids);
  if(!steps || !steps.length) return;
  const html = buildHowToHtml(steps);
  const wrapper = document.createElement("div");
  wrapper.innerHTML = html;
  const card = wrapper.firstElementChild;
  if(!card) return;
  insertHowTo(card);
}

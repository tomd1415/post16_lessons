
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
    label: "Student",
    items: [
      { label: "Student hub", href: "/index.html" },
      { label: "Course catalogue", href: "/index.html#catalog" }
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
      { label: "Pupil activity", href: "/teacher-pupil-activity.html" },
      { label: "Student hub", href: "/index.html" }
    ]
  },
  admin: {
    label: "Admin",
    items: [
      { label: "Admin home", href: "/admin.html" },
      { label: "Audit log", href: "/admin-audit.html" },
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

function renderHintSummary(value){
  if(!value || typeof value !== "object" || Array.isArray(value)) return "";
  const hints = value.hintsUsed || value.hints_used;
  if(!hints) return "";
  const labels = [];
  if(Array.isArray(hints)){
    hints.forEach(item => {
      if(!item) return;
      if(typeof item === "string") labels.push(item);
      else if(typeof item === "object") labels.push(item.label || item.step || "Hint");
    });
  }else if(typeof hints === "object"){
    Object.entries(hints).forEach(([key, val]) => {
      if(!val) return;
      if(typeof val === "string") labels.push(val);
      else if(typeof val === "object") labels.push(val.label || val.step || key);
      else labels.push(key);
    });
  }
  const unique = Array.from(new Set(labels.map(label => label && String(label).trim()).filter(Boolean)));
  if(!unique.length) return "";
  const list = unique.map(escapeHtml).join(", ");
  return `<div class="note warn" style="margin-bottom:10px"><b>Hints used:</b> ${list}</div>`;
}

function renderStateReadable(value){
  if(value === null || value === undefined || value === ""){
    return "";
  }
  const summary = renderHintSummary(value);
  return `<div class="state-view">${summary}${renderStateNode(value, null)}</div>`;
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

function normalizedPath(href){
  try{ return new URL(href, window.location.origin).pathname; }catch{ return href; }
}

function isActiveLink(href){
  const current = window.location.pathname || "/";
  return normalizedPath(href) === current;
}

const BREADCRUMB_RULES = [
  {
    test: path => path.startsWith("/admin-audit"),
    trail: (role) => [
      { label: "Admin", href: "/admin.html" },
      { label: "Audit log" }
    ]
  },
  {
    test: path => path.startsWith("/admin"),
    trail: (role) => [
      { label: "Admin", href: "/admin.html" }
    ]
  },
  {
    test: path => path.startsWith("/teacher-view"),
    trail: (role) => [
      { label: "Teacher hub", href: "/teacher.html" },
      { label: "Teacher view" }
    ]
  },
  {
    test: path => path.startsWith("/teacher-stats"),
    trail: (role) => [
      { label: "Teacher hub", href: "/teacher.html" },
      { label: "Teacher stats" }
    ]
  },
  {
    test: path => path.startsWith("/teacher-history"),
    trail: (role) => [
      { label: "Teacher hub", href: "/teacher.html" },
      { label: "Revision history" }
    ]
  },
  {
    test: path => path.startsWith("/teacher-links"),
    trail: (role) => [
      { label: "Teacher hub", href: "/teacher.html" },
      { label: "Link registry" }
    ]
  },
  {
    test: path => path.startsWith("/teacher-pupil-activity"),
    trail: (role) => [
      { label: "Teacher hub", href: "/teacher.html" },
      { label: "Teacher view", href: "/teacher-view.html" },
      { label: "Pupil activity" }
    ]
  },
  {
    test: path => /\/lessons\/lesson-\d+\/activities\//.test(path),
    trail: (role, path) => {
      const match = /\/lessons\/(lesson-(\d+))\/activities\/(\d+)/.exec(path) || [];
      const lessonSlug = match[1];
      const lessonNum = match[2];
      const activityNum = match[3];
      const lessonLabel = lessonNum ? `Lesson ${lessonNum}` : "Lesson";
      const activityLabel = activityNum ? `Activity ${activityNum}` : "Activity";
      const lessonPath = role === "teacher" || role === "admin"
        ? `/${lessonSlug}/index.html`.replace("lesson-", "lessons/lesson-")
        : `/${lessonSlug}/student.html`.replace("lesson-", "lessons/lesson-");
      return [
        role === "teacher" || role === "admin"
          ? { label: "Teacher hub", href: "/teacher.html" }
          : { label: "Student hub", href: "/index.html" },
        { label: lessonLabel, href: lessonPath },
        { label: activityLabel }
      ];
    }
  },
  {
    test: path => /\/lessons\/lesson-\d+\//.test(path),
    trail: (role, path) => {
      const match = /\/lessons\/(lesson-(\d+))\//.exec(path) || [];
      const lessonNum = match[2];
      const lessonLabel = lessonNum ? `Lesson ${lessonNum}` : "Lesson";
      return [
        role === "teacher" || role === "admin"
          ? { label: "Teacher hub", href: "/teacher.html" }
          : { label: "Student hub", href: "/index.html" },
        { label: lessonLabel }
      ];
    }
  }
];

function breadcrumbBase(role){
  if(role === "teacher" || role === "admin") return [{ label: "Teacher hub", href: "/teacher.html" }];
  return [{ label: "Student hub", href: "/index.html" }];
}

function resolveBreadcrumb(role){
  const path = window.location.pathname || "/";
  for(const rule of BREADCRUMB_RULES){
    if(rule.test(path)){
      const trail = typeof rule.trail === "function" ? rule.trail(role, path) : rule.trail;
      if(trail && trail.length) return trail;
    }
  }
  const fallback = document.title || "This page";
  return [...breadcrumbBase(role), { label: fallback }];
}

function renderBreadcrumb(trail){
  if(!trail || !trail.length) return "";
  return trail.map((item, idx)=>{
    const isLast = idx === trail.length - 1;
    if(!isLast && item.href){
      return `<a href="${escapeHtml(item.href)}">${escapeHtml(item.label)}</a>`;
    }
    return `<span class="crumb-current">${escapeHtml(item.label)}</span>`;
  }).join('<span class="crumb-sep">/</span>');
}

function renderRoleMenu(menuKey){
  if(!roleMenuHost) return;
  const menu = ROLE_MENUS[menuKey] || ROLE_MENUS.pupil;
  const items = menu.items
    .map(item => {
      const active = isActiveLink(item.href);
      return `<a class="nav-item ${active ? "active" : ""}" href="${escapeHtml(item.href)}">${escapeHtml(item.label)}</a>`;
    })
    .join("");
  const breadcrumbHtml = renderBreadcrumb(resolveBreadcrumb(menuKey));
  roleMenuHost.innerHTML = `
    <nav class="global-nav" aria-label="${escapeHtml(menu.label)} navigation">
      ${items}
    </nav>
    <div class="breadcrumb" aria-label="Breadcrumb">
      ${breadcrumbHtml}
    </div>
  `;
}

function initRoleMenu(){
  const container = $(".topbar .container");
  if(!container) return;
  let header = container.querySelector(".top-header");
  if(!header){
    header = document.createElement("div");
    header.className = "top-header";
    const brand = container.querySelector(".brand");
    if(brand){
      header.appendChild(brand);
    }
    container.prepend(header);
  }

  container.querySelectorAll(".pill").forEach(el => el.remove());

  let actions = header.querySelector(".session-actions");
  if(!actions){
    actions = document.createElement("div");
    actions.className = "session-actions";
    header.appendChild(actions);
  }

  let navRow = container.querySelector(".nav-row");
  if(!navRow){
    navRow = document.createElement("div");
    navRow.className = "nav-row";
    container.appendChild(navRow);
  }

  roleMenuHost = navRow.querySelector("#roleMenu");
  if(!roleMenuHost){
    roleMenuHost = document.createElement("div");
    roleMenuHost.id = "roleMenu";
    roleMenuHost.className = "nav-host";
    navRow.appendChild(roleMenuHost);
  }

  ["#userBadge", "#teacherToggle", "#logoutBtn", "#loginBtn"].forEach(sel => {
    const el = container.querySelector(sel);
    if(el){
      el.style.display = "";
      actions.appendChild(el);
    }
  });

  const stored = readStoredRole();
  const menuKey = stored ? roleToMenu(stored) : "pupil";
  renderRoleMenu(menuKey);
  if(roleMenuHost && !roleMenuHost.textContent.trim()){
    renderRoleMenu("pupil");
  }
}

function updateRoleMenu(role){
  if(!roleMenuHost) return;
  const menuKey = role ? roleToMenu(role) : "pupil";
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
  btn.setAttribute("aria-pressed", on ? "true" : "false");
  btn.addEventListener("click", ()=>{
    const now = !getTeacherMode(role);
    setTeacherMode(now);
    btn.textContent = now ? "Teacher mode: ON" : "Teacher mode: OFF";
    btn.setAttribute("aria-pressed", now ? "true" : "false");
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

function shuffleActivityChoices(root){
  if(!root || typeof root.querySelectorAll !== "function") return;

  const parents = new Set();
  root.querySelectorAll("label.choice").forEach(label => {
    if(label.parentElement) parents.add(label.parentElement);
  });

  parents.forEach(parent => {
    if(parent.dataset.choicesShuffled === "1") return;
    const elementChildren = Array.from(parent.children);
    const labels = elementChildren.filter(child => child.matches("label.choice"));
    if(labels.length < 2) return;
    if(!labels.every(label => label.querySelector("input[type='radio']"))) return;
    if(elementChildren.length !== labels.length) return;
    if(!elementChildren.every(child => child.matches("label.choice"))) return;
    shuffle(labels).forEach(label => parent.appendChild(label));
    parent.dataset.choicesShuffled = "1";
  });

  root.querySelectorAll("select[data-field]").forEach(select => {
    if(select.dataset.choicesShuffled === "1") return;
    const options = Array.from(select.querySelectorAll("option"));
    if(options.length < 2) return;
    const first = options[0];
    const firstText = first.textContent.trim().toLowerCase();
    const keepFirst = first.value === "" || first.disabled || firstText === "--" || firstText.startsWith("select") || firstText.startsWith("choose");
    const rest = keepFirst ? options.slice(1) : options;
    if(rest.length < 2) return;
    const currentValue = select.value;
    const shuffled = shuffle(rest);
    select.innerHTML = "";
    if(keepFirst) select.appendChild(first);
    shuffled.forEach(opt => select.appendChild(opt));
    select.value = currentValue;
    select.dataset.choicesShuffled = "1";
  });
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

const scriptUrl = document.currentScript ? document.currentScript.src : window.location.href;
function loadCoreModule(name){
  try{
    const url = new URL(name, scriptUrl).toString();
    return import(url);
  }catch{
    return Promise.reject(new Error("Module load failed"));
  }
}

function initUi(){
  initRoleMenu();
  initTeacherToggle();
  loadCoreModule("./app-activities.js")
    .then(mod => {
      if(mod && typeof mod.initActivityBrief === "function") mod.initActivityBrief();
      if(mod && typeof mod.initActivityHowTo === "function") mod.initActivityHowTo();
    })
    .catch(()=>{});
}

if(document.readyState === "loading"){
  document.addEventListener("DOMContentLoaded", initUi);
}else{
  initUi();
}


/* Minimal helpers (offline-friendly) */
const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

const store = {
  get(key, fallback=null){
    try{ const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; }catch{ return fallback; }
  },
  set(key, value){
    try{ localStorage.setItem(key, JSON.stringify(value)); }catch{}
  },
  del(key){ try{ localStorage.removeItem(key); }catch{} }
};

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
  initTeacherToggle();
});

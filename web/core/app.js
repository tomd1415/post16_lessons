
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

function getTeacherMode(){
  const params = new URLSearchParams(location.search);
  if(params.get("teacher")==="1") return true;
  return store.get("tlac_teacher_mode", false);
}
function setTeacherMode(on){
  store.set("tlac_teacher_mode", !!on);
  document.documentElement.dataset.teacher = on ? "1" : "0";
}
function initTeacherToggle(){
  const btn = $("#teacherToggle");
  if(!btn) return;
  const on = getTeacherMode();
  setTeacherMode(on);
  btn.textContent = on ? "Teacher mode: ON" : "Teacher mode: OFF";
  btn.addEventListener("click", ()=>{
    const now = !getTeacherMode();
    setTeacherMode(now);
    btn.textContent = now ? "Teacher mode: ON" : "Teacher mode: OFF";
    toast(now ? "Teacher mode enabled" : "Teacher mode disabled");
    // reveal/hide teacher-only blocks
    $$(".teacher-only").forEach(e => e.style.display = now ? "" : "none");
  });
  // initial apply
  $$(".teacher-only").forEach(e => e.style.display = on ? "" : "none");
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

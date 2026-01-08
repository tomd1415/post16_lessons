(function(){
  const host = document.getElementById("catalog");
  if(!host) return;

  const manifestUrl = host.dataset.manifest || "./lessons/manifest.json";
  const mode = host.dataset.mode || "student";

  function escapeHtml(s){
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function statusLabel(status){
    if(status === "ready") return "Ready";
    if(status === "placeholder") return "Coming soon";
    return status || "Unknown";
  }

  function renderLesson(lesson){
    const link = mode === "teacher" ? lesson.teacherPath : lesson.studentPath;
    const hasLink = Boolean(link);
    const objectives = lesson.objectives || [];
    const activities = lesson.activities || [];
    const summary = lesson.summary || "";
    const title = lesson.title || "Untitled lesson";
    const number = lesson.number !== undefined ? `Lesson ${lesson.number}` : "Lesson";

    const secondary = mode === "teacher" && lesson.studentPath
      ? `<small><a href="${lesson.studentPath}">Open student view</a></small>`
      : "";

    const teacherResources = mode === "teacher" && Array.isArray(lesson.teacherResources) && lesson.teacherResources.length
      ? `<div style="margin-top:8px"><small>Teacher resources:</small><ul class="list">${lesson.teacherResources
          .map(r => `<li><a href="${r.path}">${escapeHtml(r.title)}</a></li>`)
          .join("")}</ul></div>`
      : "";

    return `
      <div class="card">
        <div class="row" style="justify-content:space-between; align-items:flex-start">
          <div>
            <small class="muted">${escapeHtml(number)}</small>
            <h3>${escapeHtml(title)}</h3>
          </div>
          <span class="tag">${escapeHtml(statusLabel(lesson.status))}</span>
        </div>
        <p>${escapeHtml(summary)}</p>
        <small>Objectives: ${objectives.length} - Activities: ${activities.length}</small>
        <div class="row" style="margin-top:10px">
          ${hasLink ? `<a class="btn primary" href="${link}">${mode === "teacher" ? "Open teacher hub" : "Open lesson"}</a>` : ""}
          ${secondary}
        </div>
        ${teacherResources}
      </div>
    `;
  }

  function render(data){
    const lessons = (data && data.lessons) ? data.lessons.slice() : [];
    lessons.sort((a,b)=> (a.number||0) - (b.number||0));
    if(!lessons.length){
      host.innerHTML = "<div class=\"card\"><b>No lessons found.</b></div>";
      return;
    }
    host.innerHTML = lessons.map(renderLesson).join("");
  }

  fetch(manifestUrl)
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(render)
    .catch(()=>{
      host.innerHTML = "<div class=\"card\"><b>Catalogue unavailable.</b><br><small>Check the manifest path or run the site via the local server.</small></div>";
    });
})();

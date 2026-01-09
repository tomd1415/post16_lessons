(function(){
  const host = document.getElementById("roleMenu");
  if(!host) return;

  const MENUS = {
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
        { label: "Revision history", href: "/teacher-history.html" },
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
        { label: "Create user", href: "/admin.html#admin-create-user" },
        { label: "Import CSV", href: "/admin.html#admin-import" },
        { label: "Revision history", href: "/teacher-history.html" },
        { label: "Teacher hub", href: "/teacher.html" },
        { label: "Student hub", href: "/index.html" }
      ]
    }
  };

  function escapeHtml(s){
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function roleToMenu(role){
    if(role === "admin") return "admin";
    if(role === "teacher") return "teacher";
    return "pupil";
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

  function render(menuKey){
    const menu = MENUS[menuKey] || MENUS.pupil;
    const items = menu.items
      .map(item => `<li><a href="${escapeHtml(item.href)}">${escapeHtml(item.label)}</a></li>`)
      .join("");
    host.innerHTML = `
      <div class="row" style="justify-content:space-between; align-items:flex-start">
        <h2 style="margin:0">Menu</h2>
        <span class="tag">${escapeHtml(menu.label)}</span>
      </div>
      <ul class="list">
        ${items}
      </ul>
    `;
  }

  const preferred = host.dataset.menu || "pupil";
  const initialRole = document.documentElement.dataset.role || readStoredRole();
  render(initialRole ? roleToMenu(initialRole) : preferred);

  if(window.tlacAuthReady){
    window.tlacAuthReady.then(data => {
      if(data && data.user && data.user.role){
        render(roleToMenu(data.user.role));
      }
    }).catch(()=>{});
  }
})();

window.tlacAuthReady = (async function(){
  function isStaffRole(role){
    return role === "teacher" || role === "admin";
  }

  function roleAllows(required, role){
    if(!required) return true;
    if(required === "admin") return role === "admin";
    if(required === "teacher") return isStaffRole(role);
    return true;
  }

  function enforceRoleGate(user){
    const required = document.body ? document.body.dataset.requiresRole : "";
    if(!required) return;
    if(!user){
      const next = encodeURIComponent(window.location.pathname);
      window.location.href = `/login.html?next=${next}`;
      return;
    }
    if(roleAllows(required, user.role)) return;
    if(required === "admin" && user.role === "teacher"){
      window.location.href = "/teacher.html";
      return;
    }
    window.location.href = "/index.html";
  }

  async function getMe(){
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    if(!res.ok) return null;
    return res.json();
  }

  const data = await getMe();
  const user = data && data.user ? data.user : null;
  enforceRoleGate(user);
  if(!user){
    return null;
  }

  try{ localStorage.setItem("tlac_role", JSON.stringify(user.role)); }catch{}
  document.documentElement.dataset.role = user.role;
  const badge = document.getElementById("userBadge");
  if(badge){
    badge.textContent = `${user.username} (${user.role})`;
    badge.style.display = "inline-flex";
  }

  const adminLink = document.getElementById("adminLink");
  if(adminLink && user.role === "admin"){
    adminLink.style.display = "inline-flex";
  }

  const teacherLink = document.getElementById("teacherLink");
  if(teacherLink){
    teacherLink.style.display = isStaffRole(user.role) ? "inline-flex" : "none";
  }

  const logoutBtn = document.getElementById("logoutBtn");
  if(logoutBtn){
    logoutBtn.addEventListener("click", async ()=>{
      const res = await fetch("/api/auth/logout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": data.csrf_token
        },
        credentials: "same-origin"
      });
      if(res.ok){
        try{ localStorage.removeItem("tlac_role"); }catch{}
        window.location.href = "/login.html";
      }
    });
  }

  return data;
})();

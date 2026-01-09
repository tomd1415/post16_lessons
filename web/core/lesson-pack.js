(() => {
  const root = document.querySelector("[data-lesson-id]");
  if (!root) return;

  const lessonId = root.dataset.lessonId;
  const lessonRole = root.dataset.lessonRole || "student";
  const manifestUrl = root.dataset.manifest || "/lessons/manifest.json";

  const setText = (selector, value) => {
    const nodes = root.querySelectorAll(selector);
    nodes.forEach(node => {
      node.textContent = value || "";
    });
  };

  const escapeHtml = (value) => {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  };

  const renderList = (container, items, renderer, emptyText) => {
    if (!container) return;
    if (!items || !items.length) {
      container.innerHTML = `<li><small class="muted">${escapeHtml(emptyText)}</small></li>`;
      return;
    }
    container.innerHTML = items.map(renderer).join("");
  };

  const renderLinks = (container, items) => {
    if (!container) return;
    if (!items || !items.length) {
      container.innerHTML = `<li><small class="muted">No external resources listed yet.</small></li>`;
      return;
    }
    container.innerHTML = items.map(item => {
      const label = escapeHtml(item.title || item.id);
      const url = escapeHtml(item.effective_url || item.replacement_url || item.replacementUrl || item.local_path || item.localPath || item.url || "");
      const status = item.status ? ` <span class="tag">${escapeHtml(item.status)}</span>` : "";
      const meta = item.last_checked ? ` <small class="muted">Checked: ${escapeHtml(item.last_checked)}</small>` : "";
      const linkText = url ? `<a href="${url}" target="_blank" rel="noopener">${label}</a>` : label;
      return `<li>${linkText}${status}${meta}</li>`;
    }).join("");
  };

  const matchLessonId = (item) => {
    return item.lessonId === lessonId || item.lesson_id === lessonId;
  };

  const pickLinkItems = (data) => {
    const registry = (data && data.linksRegistry && data.linksRegistry.items) || [];
    return registry.filter(matchLessonId);
  };

  const pickLinkItemsFromApi = async () => {
    if (lessonRole === "student") return null;
    try {
      const res = await fetch("/api/teacher/links", { credentials: "same-origin" });
      if (!res.ok) return null;
      const data = await res.json();
      const items = Array.isArray(data.items) ? data.items : [];
      return items.filter(matchLessonId);
    } catch {
      return null;
    }
  };

  const renderLesson = async (data) => {
    const lessons = (data && data.lessons) ? data.lessons : [];
    const lesson = lessons.find(item => item.id === lessonId);
    if (!lesson) {
      setText("[data-lesson-title]", "Lesson not found");
      return;
    }

    setText("[data-lesson-title]", lesson.title);
    setText("[data-lesson-summary]", lesson.summary);
    setText("[data-lesson-timings]", lesson.timings);

    renderList(
      root.querySelector("[data-lesson-objectives]"),
      lesson.objectives || [],
      obj => `<li>${escapeHtml(obj.text || obj)}</li>`,
      "Objectives to be confirmed."
    );

    renderList(
      root.querySelector("[data-lesson-activities]"),
      lesson.activities || [],
      activity => `<li><a href="${escapeHtml(activity.path)}">${escapeHtml(activity.id)} - ${escapeHtml(activity.title)}</a></li>`,
      "Activities to be confirmed."
    );

    renderList(
      root.querySelector("[data-lesson-teacher-resources]"),
      lesson.teacherResources || [],
      resource => `<li><a href="${escapeHtml(resource.path)}">${escapeHtml(resource.title)}</a></li>`,
      "Teacher resources to be confirmed."
    );

    const linksHost = root.querySelector("[data-lesson-links]");
    if (linksHost) {
      const apiLinks = await pickLinkItemsFromApi();
      const fallbackLinks = pickLinkItems(data);
      renderLinks(linksHost, apiLinks && apiLinks.length ? apiLinks : fallbackLinks);
    }
  };

  fetch(manifestUrl)
    .then(res => res.ok ? res.json() : Promise.reject())
    .then(renderLesson)
    .catch(() => {
      setText("[data-lesson-title]", "Lesson unavailable");
    });
})();

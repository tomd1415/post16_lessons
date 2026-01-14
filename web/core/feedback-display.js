/**
 * Feedback display module for pupils
 * Shows teacher feedback banners on lesson and activity pages
 */
(() => {
  const root = document.querySelector("[data-lesson-id]");
  if (!root) return;

  const lessonId = root.dataset.lessonId;
  const activityId = root.dataset.activityId || null;

  // Don't show feedback banner on teacher pages
  const isTeacherPage = root.dataset.lessonRole === "teacher" ||
    root.hasAttribute("data-requires-role") ||
    window.location.pathname.includes("teacher") ||
    window.location.pathname.includes("admin");

  if (isTeacherPage) return;

  const escapeHtml = (s) => {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  };

  const formatDate = (iso) => {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleDateString();
    } catch {
      return iso;
    }
  };

  const createFeedbackBanner = (feedback) => {
    const banner = document.createElement("div");
    banner.className = "note feedback-banner";
    banner.style.cssText = "background:#fffef0; border-left:4px solid #f90; margin-bottom:12px; padding:12px;";

    const teacherName = escapeHtml(feedback.teacher_name || "Your teacher");
    const date = formatDate(feedback.created_at);
    const text = escapeHtml(feedback.feedback_text);

    banner.innerHTML = `
      <div style="display:flex; align-items:center; margin-bottom:6px;">
        <strong style="flex:1;">Feedback from ${teacherName}</strong>
        <small style="color:#666;">${date}</small>
      </div>
      <div>${text}</div>
    `;
    return banner;
  };

  const showFeedbackBanners = (feedbackItems) => {
    if (!feedbackItems || !feedbackItems.length) return;

    // Find container to insert banners
    const container = root.querySelector(".container") || root;
    const firstCard = container.querySelector(".card");

    if (!firstCard) return;

    // Filter feedback for current activity if on activity page
    const relevantFeedback = activityId
      ? feedbackItems.filter(fb => fb.activity_id === activityId)
      : feedbackItems;

    if (!relevantFeedback.length) return;

    // Create a feedback section
    const feedbackSection = document.createElement("div");
    feedbackSection.className = "feedback-section";
    feedbackSection.setAttribute("aria-label", "Teacher feedback");

    relevantFeedback.forEach(fb => {
      feedbackSection.appendChild(createFeedbackBanner(fb));
    });

    // Insert before the first card
    firstCard.parentNode.insertBefore(feedbackSection, firstCard);
  };

  const loadFeedback = async () => {
    try {
      const res = await fetch(`/api/pupil/feedback/${encodeURIComponent(lessonId)}`, {
        credentials: "same-origin"
      });

      if (!res.ok) return;

      const data = await res.json();
      const items = data.items || [];

      if (items.length) {
        showFeedbackBanners(items);
      }
    } catch (err) {
      // Silently fail - feedback is not critical
      console.debug("Failed to load feedback:", err);
    }
  };

  // Wait for auth to be ready before fetching feedback
  if (window.tlacAuthReady) {
    window.tlacAuthReady.then(() => {
      loadFeedback();
    }).catch(() => {
      // Not logged in, no feedback to show
    });
  } else {
    // Fallback: try loading after a short delay
    setTimeout(loadFeedback, 500);
  }
})();

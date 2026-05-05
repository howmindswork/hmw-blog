(function () {
  // ── Reading progress bar ──────────────────────────────
  if (document.querySelector(".post-body")) {
    var bar = document.createElement("div");
    bar.id = "reading-progress";
    document.body.prepend(bar);
    var body = document.querySelector(".post-body");
    function updateProgress() {
      var rect = body.getBoundingClientRect();
      var total = body.offsetHeight;
      var scrolled = -rect.top;
      var pct = Math.min(
        100,
        Math.max(0, (scrolled / (total - window.innerHeight)) * 100),
      );
      bar.style.width = pct + "%";
    }
    window.addEventListener("scroll", updateProgress, { passive: true });
    updateProgress();
  }

  // ── Reading time on post cards ────────────────────────
  document.querySelectorAll(".post-card").forEach(function (card) {
    var excerpt = card.querySelector(".post-excerpt");
    if (!excerpt) return;
    var words = excerpt.textContent.trim().split(/\s+/).length;
    var mins = Math.max(1, Math.round((words * 8) / 200)); // estimate full post ~8x excerpt
    var date = card.querySelector(".post-date");
    if (date) {
      var badge = document.createElement("span");
      badge.className = "read-time";
      badge.textContent = mins + " min read";
      date.appendChild(badge);
    }
  });

  // ── Scroll fade-in (IntersectionObserver) ─────────────
  var io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("visible");
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.08 },
  );

  document
    .querySelectorAll(
      ".post-card, .pathway-card, .email-capture, .cta-block, .faq-item, .author-card",
    )
    .forEach(function (el) {
      el.classList.add("fade-up");
      io.observe(el);
    });

  // ── Whole-card click ──────────────────────────────────
  document.querySelectorAll(".post-card").forEach(function (card) {
    var link = card.querySelector("a");
    if (link) {
      card.addEventListener("click", function (e) {
        if (!e.target.closest("a")) window.location.href = link.href;
      });
    }
  });

  // ── Satisfying click sound ────────────────────────────
  var ctx;
  function getCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    return ctx;
  }
  function playPop() {
    try {
      var c = getCtx();
      if (c.state === "suspended") c.resume();
      var t = c.currentTime;
      // Soft woody tap — low sine drop, very quiet, 30ms total
      var o = c.createOscillator();
      var g = c.createGain();
      o.connect(g);
      g.connect(c.destination);
      o.type = "sine";
      o.frequency.setValueAtTime(320, t);
      o.frequency.exponentialRampToValueAtTime(90, t + 0.028);
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(0.022, t + 0.002);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.03);
      o.start(t);
      o.stop(t + 0.032);
    } catch (e) {}
  }
  document.addEventListener(
    "click",
    function (e) {
      var t = e.target.closest(
        "a, button, .btn-primary, .btn-secondary, .sticky-btn",
      );
      if (t) playPop();
    },
    { passive: true },
  );
})();

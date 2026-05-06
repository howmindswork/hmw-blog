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

  // ── Reading time on post cards (use static value from data-cat card if present) ──
  document.querySelectorAll(".post-card").forEach(function (card) {
    if (card.querySelector(".read-time-static")) return; // already rendered server-side
    var excerpt = card.querySelector(".post-excerpt");
    if (!excerpt) return;
    var words = excerpt.textContent.trim().split(/\s+/).length;
    var mins = Math.max(3, Math.round((words * 35) / 200));
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

  // ── Click sound ──────────────────────────────────────
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
      // Soft sine tone at 600Hz, 60ms - audible but not annoying
      var osc = c.createOscillator();
      var g = c.createGain();
      osc.connect(g);
      g.connect(c.destination);
      osc.type = "sine";
      osc.frequency.setValueAtTime(600, t);
      osc.frequency.exponentialRampToValueAtTime(300, t + 0.06);
      g.gain.setValueAtTime(0.18, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.06);
      osc.start(t);
      osc.stop(t + 0.06);
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

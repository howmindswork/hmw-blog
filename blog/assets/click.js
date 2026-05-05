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
      var t = c.currentTime;
      // Crisp transient (very brief high tap)
      var o1 = c.createOscillator(),
        g1 = c.createGain();
      o1.connect(g1);
      g1.connect(c.destination);
      o1.type = "sine";
      o1.frequency.setValueAtTime(1100, t);
      o1.frequency.exponentialRampToValueAtTime(500, t + 0.01);
      g1.gain.setValueAtTime(0, t);
      g1.gain.linearRampToValueAtTime(0.055, t + 0.003);
      g1.gain.exponentialRampToValueAtTime(0.001, t + 0.022);
      o1.start(t);
      o1.stop(t + 0.025);
      // Warm body resonance
      var o2 = c.createOscillator(),
        g2 = c.createGain();
      o2.connect(g2);
      g2.connect(c.destination);
      o2.type = "sine";
      o2.frequency.setValueAtTime(240, t);
      o2.frequency.exponentialRampToValueAtTime(110, t + 0.045);
      g2.gain.setValueAtTime(0.06, t);
      g2.gain.exponentialRampToValueAtTime(0.001, t + 0.048);
      o2.start(t);
      o2.stop(t + 0.05);
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

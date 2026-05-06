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

  // ── Premium click sound (Ruixen UI model) ────────────────
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
      // Shaped white noise: 3ms, feels like physical button press, barely audible
      var buf = c.createBufferSource();
      var len = Math.floor(c.sampleRate * 0.003); // 3ms at sample rate
      var noiseBuffer = c.createBuffer(1, len, c.sampleRate);
      var data = noiseBuffer.getChannelData(0);
      // Fill with white noise, shape with exponential decay
      for (var i = 0; i < len; i++) {
        var decay = Math.pow(1 - i / len, 4); // Smooth exponential decay
        data[i] = (Math.random() * 2 - 1) * decay; // Random noise * decay
      }
      buf.buffer = noiseBuffer;
      var g = c.createGain();
      buf.connect(g);
      g.connect(c.destination);
      g.gain.setValueAtTime(0.08, t); // 8% volume, premium and subtle
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.003);
      buf.start(t);
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

(function () {
  // Reading progress bar (post pages only)
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

  // Satisfying click sound — low bass pop, not a typewriter
  var ctx;
  function getCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    return ctx;
  }
  function playPop() {
    try {
      var c = getCtx();
      // Layer 1: bass body (warm, satisfying thud)
      var o1 = c.createOscillator();
      var g1 = c.createGain();
      o1.connect(g1);
      g1.connect(c.destination);
      o1.type = "sine";
      o1.frequency.setValueAtTime(280, c.currentTime);
      o1.frequency.exponentialRampToValueAtTime(80, c.currentTime + 0.05);
      g1.gain.setValueAtTime(0.09, c.currentTime);
      g1.gain.exponentialRampToValueAtTime(0.001, c.currentTime + 0.05);
      o1.start(c.currentTime);
      o1.stop(c.currentTime + 0.05);
      // Layer 2: brief transient click (adds crispness)
      var o2 = c.createOscillator();
      var g2 = c.createGain();
      o2.connect(g2);
      g2.connect(c.destination);
      o2.type = "triangle";
      o2.frequency.setValueAtTime(900, c.currentTime);
      o2.frequency.exponentialRampToValueAtTime(300, c.currentTime + 0.015);
      g2.gain.setValueAtTime(0.04, c.currentTime);
      g2.gain.exponentialRampToValueAtTime(0.001, c.currentTime + 0.015);
      o2.start(c.currentTime);
      o2.stop(c.currentTime + 0.015);
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

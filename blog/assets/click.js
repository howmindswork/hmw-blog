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

  // ── Click sound ──────────────────────────────────────
  var ctx;
  function getCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    return ctx;
  }
  function playPop(cb) {
    try {
      var c = getCtx();
      var resume = c.state === "suspended" ? c.resume() : Promise.resolve();
      resume.then(function () {
        var t = c.currentTime;
        var osc = c.createOscillator();
        var g = c.createGain();
        osc.connect(g);
        g.connect(c.destination);
        osc.type = "sine";
        osc.frequency.setValueAtTime(600, t);
        osc.frequency.exponentialRampToValueAtTime(300, t + 0.07);
        g.gain.setValueAtTime(0.22, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.07);
        osc.start(t);
        osc.stop(t + 0.07);
        if (cb) setTimeout(cb, 80);
      });
    } catch (e) {
      if (cb) cb();
    }
  }

  // ── Whole-card click (play sound then navigate) ───────
  document.querySelectorAll(".post-card").forEach(function (card) {
    var link = card.querySelector("a");
    if (!link) return;
    card.addEventListener("click", function (e) {
      var href = e.target.closest("a") ? e.target.closest("a").href : link.href;
      if (e.target.closest("a")) {
        e.preventDefault();
        playPop(function () {
          window.location.href = href;
        });
      } else {
        playPop(function () {
          window.location.href = href;
        });
      }
    });
  });

  // ── Moon — 20 sounds × 20 animations = endless variety ──
  var moon = document.querySelector(".hero-moon");
  if (moon) {
    moon.style.cursor = "pointer";
    moon.style.userSelect = "none";
    moon.style.webkitUserSelect = "none";

    var moonSounds = [
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "sine";
        o.frequency.setValueAtTime(880, t);
        o.frequency.exponentialRampToValueAtTime(440, t + 0.1);
        g.gain.setValueAtTime(0.25, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.1);
        o.start(t);
        o.stop(t + 0.1);
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "triangle";
        o.frequency.setValueAtTime(300, t);
        o.frequency.exponentialRampToValueAtTime(600, t + 0.08);
        g.gain.setValueAtTime(0.3, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
        o.start(t);
        o.stop(t + 0.12);
      },
      function (c, t) {
        [1, 1.26, 1.5].forEach(function (r) {
          var o = c.createOscillator(),
            g = c.createGain();
          o.connect(g);
          g.connect(c.destination);
          o.type = "sine";
          o.frequency.value = 440 * r;
          g.gain.setValueAtTime(0.12, t);
          g.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
          o.start(t);
          o.stop(t + 0.18);
        });
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "square";
        o.frequency.setValueAtTime(200, t);
        o.frequency.exponentialRampToValueAtTime(50, t + 0.06);
        g.gain.setValueAtTime(0.15, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.06);
        o.start(t);
        o.stop(t + 0.06);
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "sine";
        o.frequency.setValueAtTime(1200, t);
        o.frequency.exponentialRampToValueAtTime(800, t + 0.05);
        g.gain.setValueAtTime(0.2, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.08);
        o.start(t);
        o.stop(t + 0.08);
      },
      function (c, t) {
        [0, 0.04, 0.08].forEach(function (d) {
          var o = c.createOscillator(),
            g = c.createGain();
          o.connect(g);
          g.connect(c.destination);
          o.type = "sine";
          o.frequency.value = 660;
          g.gain.setValueAtTime(0, t + d);
          g.gain.linearRampToValueAtTime(0.2, t + d + 0.01);
          g.gain.exponentialRampToValueAtTime(0.001, t + d + 0.05);
          o.start(t + d);
          o.stop(t + d + 0.05);
        });
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "triangle";
        o.frequency.setValueAtTime(528, t);
        g.gain.setValueAtTime(0.28, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.22);
        o.start(t);
        o.stop(t + 0.22);
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "sine";
        o.frequency.setValueAtTime(400, t);
        o.frequency.setValueAtTime(800, t + 0.03);
        o.frequency.setValueAtTime(400, t + 0.06);
        g.gain.setValueAtTime(0.2, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.1);
        o.start(t);
        o.stop(t + 0.1);
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "sawtooth";
        o.frequency.setValueAtTime(120, t);
        o.frequency.exponentialRampToValueAtTime(60, t + 0.05);
        g.gain.setValueAtTime(0.12, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.05);
        o.start(t);
        o.stop(t + 0.05);
      },
      function (c, t) {
        [392, 494, 587].forEach(function (f, i) {
          var o = c.createOscillator(),
            g = c.createGain();
          o.connect(g);
          g.connect(c.destination);
          o.type = "sine";
          o.frequency.value = f;
          g.gain.setValueAtTime(0, t + i * 0.05);
          g.gain.linearRampToValueAtTime(0.15, t + i * 0.05 + 0.02);
          g.gain.exponentialRampToValueAtTime(0.001, t + i * 0.05 + 0.12);
          o.start(t + i * 0.05);
          o.stop(t + i * 0.05 + 0.12);
        });
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "sine";
        o.frequency.setValueAtTime(174, t);
        g.gain.setValueAtTime(0.3, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.3);
        o.start(t);
        o.stop(t + 0.3);
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "sine";
        o.frequency.setValueAtTime(1760, t);
        o.frequency.exponentialRampToValueAtTime(220, t + 0.15);
        g.gain.setValueAtTime(0.18, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.15);
        o.start(t);
        o.stop(t + 0.15);
      },
      function (c, t) {
        [0, 0.02, 0.04, 0.06, 0.08].forEach(function (d) {
          var o = c.createOscillator(),
            g = c.createGain();
          o.connect(g);
          g.connect(c.destination);
          o.type = "sine";
          o.frequency.value = 500 + Math.random() * 800;
          g.gain.setValueAtTime(0.08, t + d);
          g.gain.exponentialRampToValueAtTime(0.001, t + d + 0.04);
          o.start(t + d);
          o.stop(t + d + 0.04);
        });
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "triangle";
        o.frequency.setValueAtTime(440, t);
        o.frequency.linearRampToValueAtTime(880, t + 0.04);
        o.frequency.linearRampToValueAtTime(440, t + 0.08);
        g.gain.setValueAtTime(0.22, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
        o.start(t);
        o.stop(t + 0.12);
      },
      function (c, t) {
        [262, 330, 392, 523].forEach(function (f) {
          var o = c.createOscillator(),
            g = c.createGain();
          o.connect(g);
          g.connect(c.destination);
          o.type = "sine";
          o.frequency.value = f;
          g.gain.setValueAtTime(0.08, t);
          g.gain.exponentialRampToValueAtTime(0.001, t + 0.25);
          o.start(t);
          o.stop(t + 0.25);
        });
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "sine";
        o.frequency.setValueAtTime(740, t);
        o.frequency.exponentialRampToValueAtTime(370, t + 0.05);
        g.gain.setValueAtTime(0.25, t);
        g.gain.linearRampToValueAtTime(0.25, t + 0.02);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.09);
        o.start(t);
        o.stop(t + 0.09);
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "square";
        o.frequency.setValueAtTime(440, t);
        g.gain.setValueAtTime(0.05, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.03);
        o.start(t);
        o.stop(t + 0.03);
      },
      function (c, t) {
        [1, 2, 3].forEach(function (n) {
          var o = c.createOscillator(),
            g = c.createGain();
          o.connect(g);
          g.connect(c.destination);
          o.type = "sine";
          o.frequency.value = 220 * n;
          g.gain.setValueAtTime(0.1 / n, t);
          g.gain.exponentialRampToValueAtTime(0.001, t + 0.2);
          o.start(t);
          o.stop(t + 0.2);
        });
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "triangle";
        o.frequency.setValueAtTime(1000, t);
        o.frequency.exponentialRampToValueAtTime(500, t + 0.03);
        o.frequency.exponentialRampToValueAtTime(1000, t + 0.06);
        g.gain.setValueAtTime(0.2, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.1);
        o.start(t);
        o.stop(t + 0.1);
      },
      function (c, t) {
        var o = c.createOscillator(),
          g = c.createGain();
        o.connect(g);
        g.connect(c.destination);
        o.type = "sine";
        o.frequency.setValueAtTime(432, t);
        g.gain.setValueAtTime(0.3, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
        o.start(t);
        o.stop(t + 0.35);
      },
    ];

    var moonAnims = [
      function (m) {
        m.style.transition = "transform 0.15s ease";
        m.style.transform = "scale(1.5) rotate(-20deg)";
        setTimeout(function () {
          m.style.transform = "";
        }, 160);
      },
      function (m) {
        m.style.transition = "transform 0.2s cubic-bezier(.36,.07,.19,.97)";
        m.style.transform = "scale(1.6) rotate(360deg)";
        setTimeout(function () {
          m.style.transition = "transform 0.15s ease";
          m.style.transform = "";
        }, 220);
      },
      function (m) {
        m.style.transition = "transform 0.08s ease";
        m.style.transform = "translateY(-18px) scale(1.2)";
        setTimeout(function () {
          m.style.transition = "transform 0.2s cubic-bezier(.4,0,.2,1)";
          m.style.transform = "";
        }, 100);
      },
      function (m) {
        var s = [
          "scale(1.1) rotate(10deg)",
          "scale(0.9) rotate(-10deg)",
          "scale(1.1) rotate(8deg)",
          "scale(1) rotate(0)",
        ];
        s.forEach(function (v, i) {
          setTimeout(function () {
            m.style.transition = "transform 0.06s ease";
            m.style.transform = v;
          }, i * 60);
        });
      },
      function (m) {
        m.style.transition = "transform 0.12s ease";
        m.style.transform = "scale(0.6)";
        setTimeout(function () {
          m.style.transition = "transform 0.2s cubic-bezier(.17,.67,.41,1.6)";
          m.style.transform = "scale(1)";
        }, 130);
      },
      function (m) {
        m.style.transition = "transform 0.1s ease";
        m.style.transform = "translateX(-12px) scale(1.1)";
        setTimeout(function () {
          m.style.transition = "transform 0.1s ease";
          m.style.transform = "translateX(12px)";
          setTimeout(function () {
            m.style.transition = "transform 0.15s ease";
            m.style.transform = "";
          }, 100);
        }, 100);
      },
      function (m) {
        m.style.transition = "transform 0.18s ease";
        m.style.transform = "scale(1.8) rotate(-5deg)";
        setTimeout(function () {
          m.style.transition = "transform 0.3s cubic-bezier(.4,0,.2,1)";
          m.style.transform = "";
        }, 200);
      },
      function (m) {
        m.style.transition = "transform 0.15s ease";
        m.style.transform = "scaleX(1.6) scaleY(0.7)";
        setTimeout(function () {
          m.style.transition = "transform 0.2s cubic-bezier(.17,.67,.41,1.4)";
          m.style.transform = "scaleX(0.8) scaleY(1.3)";
          setTimeout(function () {
            m.style.transition = "transform 0.15s ease";
            m.style.transform = "";
          }, 180);
        }, 160);
      },
      function (m) {
        m.style.transition = "transform 0.3s cubic-bezier(.17,.67,.41,1.5)";
        m.style.transform = "scale(1.4) rotate(180deg)";
        setTimeout(function () {
          m.style.transform = "scale(1) rotate(360deg)";
        }, 320);
      },
      function (m) {
        var frames = [
          "translateY(-6px)",
          "translateY(4px)",
          "translateY(-3px)",
          "translateY(2px)",
          "translateY(0)",
        ];
        frames.forEach(function (v, i) {
          setTimeout(function () {
            m.style.transition = "transform 0.05s ease";
            m.style.transform = v;
          }, i * 55);
        });
      },
      function (m) {
        m.style.transition = "transform 0.1s ease";
        m.style.transform = "scale(1.3) skewX(15deg)";
        setTimeout(function () {
          m.style.transition = "transform 0.15s ease";
          m.style.transform = "scale(1.1) skewX(-10deg)";
          setTimeout(function () {
            m.style.transition = "transform 0.12s ease";
            m.style.transform = "";
          }, 140);
        }, 110);
      },
      function (m) {
        m.style.transition = "transform 0.4s cubic-bezier(.17,.67,.41,1.6)";
        m.style.transform = "scale(2) rotate(15deg)";
        setTimeout(function () {
          m.style.transition = "transform 0.2s ease";
          m.style.transform = "";
        }, 420);
      },
      function (m) {
        m.style.transition = "filter 0.1s ease, transform 0.1s ease";
        m.style.filter = "brightness(3) drop-shadow(0 0 20px #a78bfa)";
        m.style.transform = "scale(1.2)";
        setTimeout(function () {
          m.style.transition = "filter 0.3s ease, transform 0.3s ease";
          m.style.filter = "";
          m.style.transform = "";
        }, 120);
      },
      function (m) {
        m.style.transition = "transform 0.08s ease";
        m.style.transform = "rotate(25deg) scale(1.2)";
        setTimeout(function () {
          m.style.transition = "transform 0.08s ease";
          m.style.transform = "rotate(-25deg)";
          setTimeout(function () {
            m.style.transition = "transform 0.08s ease";
            m.style.transform = "rotate(15deg)";
            setTimeout(function () {
              m.style.transition = "transform 0.12s ease";
              m.style.transform = "";
            }, 80);
          }, 80);
        }, 80);
      },
      function (m) {
        m.style.transition = "transform 0.5s cubic-bezier(.17,.67,.83,1.3)";
        m.style.transform = "translateY(-30px) scale(1.3)";
        setTimeout(function () {
          m.style.transition = "transform 0.3s cubic-bezier(.4,0,.2,1)";
          m.style.transform = "";
        }, 520);
      },
      function (m) {
        m.style.transition = "transform 0.12s ease";
        m.style.transform = "scale(1.4) rotate(-360deg)";
        setTimeout(function () {
          m.style.transition = "transform 0.2s ease";
          m.style.transform = "scale(1) rotate(-360deg)";
        }, 130);
      },
      function (m) {
        [1.2, 0.85, 1.1, 0.95, 1].forEach(function (s, i) {
          setTimeout(function () {
            m.style.transition = "transform 0.07s ease";
            m.style.transform = "scale(" + s + ")";
          }, i * 70);
        });
      },
      function (m) {
        m.style.transition = "transform 0.15s ease";
        m.style.transform = "scale(1.3) translateX(10px) translateY(-10px)";
        setTimeout(function () {
          m.style.transition = "transform 0.15s ease";
          m.style.transform = "scale(0.9) translateX(-8px) translateY(8px)";
          setTimeout(function () {
            m.style.transition = "transform 0.2s ease";
            m.style.transform = "";
          }, 150);
        }, 150);
      },
      function (m) {
        m.style.transition = "transform 0.06s linear";
        m.style.transform = "scaleX(-1)";
        setTimeout(function () {
          m.style.transition = "transform 0.06s linear";
          m.style.transform = "scaleX(1)";
        }, 100);
      },
      function (m) {
        m.style.transition = "transform 0.2s ease, filter 0.2s ease";
        m.style.transform = "scale(1.5)";
        m.style.filter = "hue-rotate(180deg) drop-shadow(0 0 15px #818cf8)";
        setTimeout(function () {
          m.style.transition = "transform 0.3s ease, filter 0.3s ease";
          m.style.transform = "";
          m.style.filter = "";
        }, 230);
      },
    ];

    var moonClickCount = 0;
    moon.addEventListener("click", function (e) {
      e.stopPropagation();
      var si = moonClickCount % moonSounds.length;
      var ai = Math.floor(Math.random() * moonAnims.length);
      moonClickCount++;
      try {
        var c = getCtx();
        var resume = c.state === "suspended" ? c.resume() : Promise.resolve();
        resume.then(function () {
          moonSounds[si](c, c.currentTime);
        });
      } catch (err) {}
      moonAnims[ai](moon);
    });
  }

  // ── All other clickable elements ───────────────────────
  document.addEventListener(
    "click",
    function (e) {
      var t = e.target.closest(
        "a, button, .btn-primary, .btn-secondary, .sticky-btn, .filter-btn, .nav-link, .nav-brand",
      );
      if (t && !e.target.closest(".post-card")) playPop();
    },
    { passive: true },
  );
})();

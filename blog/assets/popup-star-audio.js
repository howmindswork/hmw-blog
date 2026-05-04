(function () {
  var STORAGE_KEY = 'hmw_star_popup_dismissed';
  var WORKER_URL = 'https://star-audio-capture.howmindswork.workers.dev';
  var DELAY_MS = 8000;

  function isDismissed() {
    try {
      var val = localStorage.getItem(STORAGE_KEY);
      if (!val) return false;
      return Date.now() < parseInt(val, 10);
    } catch (e) { return false; }
  }

  function dismiss() {
    try {
      localStorage.setItem(STORAGE_KEY, Date.now() + 7 * 24 * 60 * 60 * 1000);
    } catch (e) {}
    var el = document.getElementById('hmw-star-popup');
    if (!el) return;
    el.style.opacity = '0';
    setTimeout(function () { if (el) el.remove(); }, 350);
  }

  function injectStyles() {
    var css = [
      '#hmw-star-popup{',
        'position:fixed;inset:0;z-index:99999;',
        'display:flex;align-items:center;justify-content:center;',
        'background:rgba(4,3,2,0.82);',
        'backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);',
        'opacity:0;transition:opacity 0.4s ease;',
        'padding:1.5rem;',
      '}',
      '#hmw-star-popup.visible{opacity:1;}',
      '#hmw-star-box{',
        'position:relative;',
        'background:#0c0b08;',
        'border:1px solid #2e2a20;',
        'border-top:2px solid #c9871c;',
        'border-radius:4px;',
        'max-width:420px;width:100%;',
        'padding:2.5rem 2.25rem 2rem;',
        'text-align:center;',
        'box-shadow:0 0 60px rgba(201,135,28,0.07),0 24px 64px rgba(0,0,0,0.6);',
        'overflow:hidden;',
      '}',
      '#hmw-star-box::before{',
        'content:"";position:absolute;top:-80px;left:50%;transform:translateX(-50%);',
        'width:300px;height:300px;',
        'background:radial-gradient(circle,rgba(201,135,28,0.07) 0%,transparent 70%);',
        'pointer-events:none;',
      '}',
      '#hmw-star-close{',
        'position:absolute;top:14px;right:16px;',
        'background:none;border:none;cursor:pointer;',
        'color:#5c5347;font-size:1.1rem;line-height:1;',
        'padding:4px;transition:color 0.2s;',
      '}',
      '#hmw-star-close:hover{color:#ede5d8;}',
      '#hmw-star-moon{',
        'font-size:2rem;display:block;margin-bottom:1rem;',
        'animation:hmw-moon-glow 3s ease-in-out infinite;',
      '}',
      '@keyframes hmw-moon-glow{',
        '0%,100%{filter:drop-shadow(0 0 6px rgba(201,135,28,0.4));}',
        '50%{filter:drop-shadow(0 0 18px rgba(201,135,28,0.75));}',
      '}',
      '#hmw-star-eyebrow{',
        'font-family:Inter,sans-serif;',
        'font-size:0.68rem;font-weight:600;letter-spacing:0.16em;',
        'text-transform:uppercase;color:#c9871c;',
        'margin-bottom:0.8rem;display:block;',
      '}',
      '#hmw-star-headline{',
        'font-family:Newsreader,serif;',
        'font-size:1.45rem;font-weight:500;line-height:1.25;letter-spacing:-0.02em;',
        'color:#ede5d8;margin:0 0 0.65rem;',
      '}',
      '#hmw-star-sub{',
        'font-family:Inter,sans-serif;',
        'font-size:0.875rem;line-height:1.65;font-weight:300;',
        'color:#9a8e7e;margin:0 0 1.5rem;',
      '}',
      '#hmw-star-form{display:flex;flex-direction:column;gap:10px;}',
      '#hmw-star-input{',
        'background:#17150f;border:1px solid #2e2a20;border-radius:2px;',
        'color:#ede5d8;font-family:Inter,sans-serif;font-size:0.9rem;',
        'padding:13px 16px;width:100%;box-sizing:border-box;',
        'outline:none;transition:border-color 0.2s;',
      '}',
      '#hmw-star-input:focus{border-color:#c9871c;}',
      '#hmw-star-input::placeholder{color:#5c5347;}',
      '#hmw-star-submit{',
        'background:#c9871c;color:#080706;',
        'font-family:Inter,sans-serif;font-weight:700;',
        'font-size:0.875rem;letter-spacing:0.05em;text-transform:uppercase;',
        'padding:14px 20px;border-radius:2px;',
        'border:none;cursor:pointer;width:100%;',
        'transition:background 0.2s,box-shadow 0.2s;',
      '}',
      '#hmw-star-submit:hover:not(:disabled){background:#e8a032;box-shadow:0 0 20px rgba(201,135,28,0.3);}',
      '#hmw-star-submit:disabled{opacity:0.6;cursor:default;}',
      '#hmw-star-success{',
        'font-family:Newsreader,serif;font-size:1.2rem;',
        'color:#ede5d8;line-height:1.5;padding:0.5rem 0;',
      '}',
      '#hmw-star-note{',
        'font-family:Inter,sans-serif;',
        'font-size:0.7rem;color:#5c5347;margin-top:0.75rem;display:block;',
      '}',
    ].join('');
    var s = document.createElement('style');
    s.textContent = css;
    document.head.appendChild(s);
  }

  function buildPopup() {
    var overlay = document.createElement('div');
    overlay.id = 'hmw-star-popup';
    overlay.innerHTML = [
      '<div id="hmw-star-box">',
        '<button id="hmw-star-close" aria-label="Close">✕</button>',
        '<span id="hmw-star-moon">🌙</span>',
        '<span id="hmw-star-eyebrow">Free — How Minds Work</span>',
        '<h2 id="hmw-star-headline">The Star Feeding Ritual Audio</h2>',
        '<p id="hmw-star-sub">5 minutes. One clean release for the loop your brain won\'t stop running. Enter your email and it\'s yours.</p>',
        '<form id="hmw-star-form" novalidate>',
          '<input id="hmw-star-input" type="email" placeholder="Your email address" autocomplete="email" required />',
          '<button id="hmw-star-submit" type="submit">Send me the audio →</button>',
        '</form>',
        '<span id="hmw-star-note">No spam. Unsubscribe any time.</span>',
      '</div>',
    ].join('');

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) dismiss();
    });
    overlay.querySelector('#hmw-star-close').addEventListener('click', dismiss);

    overlay.querySelector('#hmw-star-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var input = document.getElementById('hmw-star-input');
      var btn = document.getElementById('hmw-star-submit');
      var email = input.value.trim();
      if (!email || !email.includes('@')) {
        input.focus();
        return;
      }
      btn.disabled = true;
      btn.textContent = 'Sending…';

      fetch(WORKER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            var form = document.getElementById('hmw-star-form');
            var note = document.getElementById('hmw-star-note');
            form.innerHTML = '<p id="hmw-star-success">Check your inbox — it\'s on its way. 🌙</p>';
            if (note) note.style.display = 'none';
            try { localStorage.setItem(STORAGE_KEY, Date.now() + 30 * 24 * 60 * 60 * 1000); } catch(e) {}
            setTimeout(dismiss, 3500);
          } else {
            btn.disabled = false;
            btn.textContent = 'Try again';
          }
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = 'Try again';
        });
    });

    document.body.appendChild(overlay);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        overlay.classList.add('visible');
      });
    });
  }

  function init() {
    if (isDismissed()) return;
    injectStyles();
    setTimeout(buildPopup, DELAY_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

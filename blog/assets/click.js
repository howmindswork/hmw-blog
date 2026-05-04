(function () {
  // Synthesize a soft click using Web Audio API — no external file needed
  function playClick() {
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var buf = ctx.createBuffer(1, ctx.sampleRate * 0.04, ctx.sampleRate);
      var data = buf.getChannelData(0);
      for (var i = 0; i < data.length; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / data.length, 8);
      }
      var src = ctx.createBufferSource();
      var gain = ctx.createGain();
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.04);
      src.buffer = buf;
      src.connect(gain);
      gain.connect(ctx.destination);
      src.start();
    } catch (e) {}
  }

  document.addEventListener('click', function (e) {
    var t = e.target.closest('a, button, .btn-primary, .btn-secondary, .post-card');
    if (t) playClick();
  });

  // Reading progress bar — inject bar div, update on scroll (post pages only)
  if (document.querySelector('.post-body')) {
    var bar = document.createElement('div');
    bar.id = 'reading-progress';
    document.body.prepend(bar);

    var body = document.querySelector('.post-body');
    function updateProgress() {
      var rect = body.getBoundingClientRect();
      var total = body.offsetHeight;
      var scrolled = -rect.top;
      var pct = Math.min(100, Math.max(0, (scrolled / (total - window.innerHeight)) * 100));
      bar.style.width = pct + '%';
    }

    window.addEventListener('scroll', updateProgress, { passive: true });
    updateProgress();
  }
})();

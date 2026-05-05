(function () {
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

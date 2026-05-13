(function () {
  const input = document.getElementById('nav-search');
  const box = document.getElementById('search-suggest');
  if (!input || !box) return;
  let t;
  input.addEventListener('input', function () {
    clearTimeout(t);
    const q = input.value.trim();
    if (q.length < 2) {
      box.classList.add('hidden');
      box.innerHTML = '';
      return;
    }
    t = setTimeout(async () => {
      try {
        const r = await fetch('/search-ajax/?q=' + encodeURIComponent(q), {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        const j = await r.json();
        if (!j.results || !j.results.length) {
          box.classList.add('hidden');
          return;
        }
        box.innerHTML =
          '<div class="rounded-2xl border border-stone-100 bg-white p-2 shadow-soft">' +
          j.results
            .map(
              (x) =>
                '<a class="block rounded-xl px-3 py-2 text-sm hover:bg-brand-50" href="/saree/' +
                x.slug +
                '/">' +
                x.name +
                ' <span class="text-xs text-stone-500">₹' +
                x.price +
                '</span></a>'
            )
            .join('') +
          '</div>';
        box.classList.remove('hidden');
      } catch (e) {
        box.classList.add('hidden');
      }
    }, 220);
  });
  document.addEventListener('click', function (e) {
    if (!box.contains(e.target) && e.target !== input) box.classList.add('hidden');
  });
})();

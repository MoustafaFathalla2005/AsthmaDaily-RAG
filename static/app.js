/* AsthmaDaily - shared front-end behaviour.
 * Kept in its own file (instead of inline in base.html) so it's easy to
 * find, lint and reuse across pages. Language switching is handled
 * server-side (see webapp.py's context processor) via the `lang` cookie;
 * this file only persists the cookie on click and shows the "saved" toast.
 */
(function () {
  function showToast(message) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-bg-primary border-0';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.innerHTML =
      '<div class="d-flex"><div class="toast-body">' + message +
      '</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
    container.appendChild(toastEl);
    const t = new bootstrap.Toast(toastEl, { delay: 3000 });
    t.show();
  }

  const params = new URLSearchParams(window.location.search);

  // Persist the language choice in a cookie so every subsequent request
  // (server-rendered) picks the right language via webapp.py's get_lang().
  if (params.get('lang')) {
    document.cookie = 'lang=' + params.get('lang') + '; path=/; max-age=' + 60 * 60 * 24 * 365;
  }

  if (params.get('saved')) {
    const msg = (window.APP_I18N && window.APP_I18N.saved) || 'Saved';
    showToast(msg);
    params.delete('saved');
    const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
    window.history.replaceState({}, document.title, newUrl);
  }
})();

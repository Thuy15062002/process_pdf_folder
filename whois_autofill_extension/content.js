(() => {
  if (window.location.pathname !== "/whois") {
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const domain = params.get("domain")?.trim();
  if (!domain) {
    return;
  }

  const fillDomain = () => {
    const input = document.querySelector('input[type="text"][name="domain"][ng-model="query"]');
    if (!input || input.disabled || input.readOnly) {
      return false;
    }

    if (input.value !== domain) {
      input.value = domain;
      // Đồng bộ giá trị mới với ng-model của AngularJS.
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
    input.focus();
    return true;
  };

  if (fillDomain()) {
    return;
  }

  const retryTimer = window.setInterval(() => {
    if (fillDomain()) {
      window.clearInterval(retryTimer);
    }
  }, 250);
  window.setTimeout(() => window.clearInterval(retryTimer), 10_000);
})();

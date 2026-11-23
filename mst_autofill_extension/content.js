(() => {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const mst = params.get("mst");
  if (!mst) {
    return;
  }

  const selectors = [
    '#ctl00_ctl36_txtSearchTerm_entHD',
    'input[name="ctl00$ctl36$txtSearchTerm_entHD"]',
    'input[title="Tên/Mã số doanh nghiệp"]',
    'input.timkiem_text',
  ];

  const findVisibleInput = () => {
    for (const selector of selectors) {
      const input = [...document.querySelectorAll(selector)].find(
        (element) => element.offsetParent !== null && !element.disabled
      );
      if (input) {
        return input;
      }
    }
    return null;
  };

  const fillAndFocusInput = () => {
    const input = findVisibleInput();
    if (!input) {
      return false;
    }

    const valueSetter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value"
    ).set;
    valueSetter.call(input, mst);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.scrollIntoView({ behavior: "smooth", block: "center" });
    input.focus({ preventScroll: true });
    input.style.outline = "3px solid #2563eb";
    window.setTimeout(() => {
      input.style.outline = "";
    }, 2_000);
    return true;
  };

  if (fillAndFocusInput()) {
    return;
  }

  const retryTimer = window.setInterval(() => {
    if (fillAndFocusInput()) {
      window.clearInterval(retryTimer);
    }
  }, 500);

  window.setTimeout(() => window.clearInterval(retryTimer), 30_000);
})();

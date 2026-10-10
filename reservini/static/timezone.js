(() => {
  const select = document.querySelector("[data-guess-timezone] select");
  if (!select || select.value !== "UTC") {
    return;
  }

  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  if ([...select.options].some((option) => option.value === zone)) {
    select.value = zone;
  }
})();

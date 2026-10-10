(() => {
  const picker = document.querySelector("[data-booking-picker]");
  if (!picker) {
    return;
  }

  const chips = [...picker.querySelectorAll("[data-day]")];
  const panels = [...picker.querySelectorAll("[data-day-panel]")];
  const periodFilter = picker.querySelector("[data-period-filter]");
  const periodButtons = [...periodFilter.querySelectorAll("button")];
  let period = "all";

  function showDay(day) {
    chips.forEach((chip) => {
      if (chip.dataset.day === day) {
        chip.setAttribute("aria-current", "date");
      } else {
        chip.removeAttribute("aria-current");
      }
    });
    panels.forEach((panel) => {
      panel.hidden = panel.dataset.dayPanel !== day;
    });

    const url = new URL(window.location.href);
    url.searchParams.set("day", day);
    window.history.replaceState(null, "", url);
  }

  function applyPeriod() {
    panels.forEach((panel) => {
      panel.querySelectorAll(".timeline-row").forEach((row) => {
        row.hidden = period !== "all" && row.dataset.period !== period;
      });
    });
    periodButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.period === period));
    });
  }

  chips.forEach((chip) => {
    chip.addEventListener("click", (event) => {
      event.preventDefault();
      showDay(chip.dataset.day);
    });
  });

  periodButtons.forEach((button) => {
    button.addEventListener("click", () => {
      period = button.dataset.period;
      applyPeriod();
    });
  });

  periodFilter.hidden = false;
})();

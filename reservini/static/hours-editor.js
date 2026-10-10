(() => {
  const editor = document.querySelector("[data-hours-editor]");
  if (!editor) {
    return;
  }

  const STEP = 30;
  const LAST_MINUTE = 23 * 60 + 30;
  const DEFAULT_RANGE = { start: 9 * 60, end: 18 * 60 };
  const RANGE = /^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$/;
  const labels = editor.dataset;

  const list = editor.querySelector("[data-hours-list]");
  const textEditor = document.querySelector("[data-hours-text]");
  const inputs = [...document.querySelectorAll('input[name^="hours-"]')];
  const dayNames = inputs.map((input) => document.querySelector(`label[for="${input.id}"]`).textContent.trim());
  const week = inputs.map((input) => parseRanges(input.value));

  function toMinutes(hours, minutes) {
    return Number(hours) * 60 + Number(minutes);
  }

  function parseRanges(text) {
    return text
      .split(",")
      .map((part) => part.trim().match(RANGE))
      .filter(Boolean)
      .map((match) => ({ start: toMinutes(match[1], match[2]), end: toMinutes(match[3], match[4]) }))
      .filter((range) => range.start < range.end);
  }

  function formatTime(minutes) {
    const hours = String(Math.floor(minutes / 60)).padStart(2, "0");
    return `${hours}:${String(minutes % 60).padStart(2, "0")}`;
  }

  function save(day) {
    week[day].sort((first, second) => first.start - second.start);
    inputs[day].value = week[day].map((range) => `${formatTime(range.start)}-${formatTime(range.end)}`).join(", ");
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text) {
      node.textContent = text;
    }
    return node;
  }

  function timeSelect(value, from, to, label) {
    const select = element("select", "hours-time-select");
    select.setAttribute("aria-label", label);
    for (let minute = from; minute <= to; minute += STEP) {
      const option = element("option", "", formatTime(minute));
      option.value = minute;
      option.selected = minute === value;
      select.append(option);
    }
    return select;
  }

  function nextRange(day) {
    const last = week[day][week[day].length - 1];
    if (!last) {
      return { ...DEFAULT_RANGE };
    }
    const start = Math.min(last.end + 60, LAST_MINUTE - STEP);
    return { start, end: Math.min(start + 4 * 60, LAST_MINUTE) };
  }

  function rangeRow(day, index, range) {
    const row = element("div", "hours-range");
    const from = timeSelect(range.start, 0, LAST_MINUTE - STEP, `${dayNames[day]}, ${labels.fromLabel}`);
    const to = timeSelect(range.end, range.start + STEP, LAST_MINUTE, `${dayNames[day]}, ${labels.toLabel}`);

    from.addEventListener("change", () => {
      range.start = Number(from.value);
      range.end = Math.max(range.end, range.start + STEP);
      save(day);
      renderDay(day);
    });
    to.addEventListener("change", () => {
      range.end = Number(to.value);
      save(day);
    });

    row.append(from, element("span", "hours-range-separator", labels.toLabel), to);

    if (week[day].length > 1) {
      const remove = element("button", "hours-icon-button", "×");
      remove.type = "button";
      remove.setAttribute("aria-label", `${labels.removeLabel} ${formatTime(range.start)}`);
      remove.addEventListener("click", () => {
        week[day].splice(index, 1);
        save(day);
        renderDay(day);
      });
      row.append(remove);
    }
    return row;
  }

  function renderDay(day) {
    const row = list.children[day];
    const isOpen = week[day].length > 0;
    row.classList.toggle("is-closed", !isOpen);
    row.querySelector("input[role=switch]").checked = isOpen;
    row.querySelector(".hours-day-status").textContent = labels.closedLabel;

    const ranges = row.querySelector(".hours-ranges");
    if (!isOpen) {
      ranges.replaceChildren();
      return;
    }

    const add = element("button", "hours-link-button", labels.addLabel);
    add.type = "button";
    add.disabled = nextRange(day).start <= week[day][week[day].length - 1].end;
    add.addEventListener("click", () => {
      week[day].push(nextRange(day));
      save(day);
      renderDay(day);
    });

    const copy = element("button", "hours-link-button", labels.copyLabel);
    copy.type = "button";
    copy.addEventListener("click", () => {
      week.forEach((_ranges, otherDay) => {
        if (otherDay !== day && week[otherDay].length > 0) {
          week[otherDay] = week[day].map((range) => ({ ...range }));
          save(otherDay);
          renderDay(otherDay);
        }
      });
      copy.textContent = labels.copiedLabel;
    });

    const actions = element("div", "hours-actions");
    actions.append(add, copy);
    ranges.replaceChildren(...week[day].map((range, index) => rangeRow(day, index, range)), actions);
  }

  function dayRow(day) {
    const row = element("div", "hours-day-row");
    const toggle = element("label", "hours-switch");
    const checkbox = element("input");
    checkbox.type = "checkbox";
    checkbox.setAttribute("role", "switch");
    checkbox.addEventListener("change", () => {
      week[day] = checkbox.checked ? [{ ...DEFAULT_RANGE }] : [];
      save(day);
      renderDay(day);
    });
    toggle.append(checkbox, element("span", "hours-switch-track"), element("span", "hours-day-name", dayNames[day]));

    row.append(toggle, element("span", "hours-day-status"), element("div", "hours-ranges"));
    return row;
  }

  inputs.forEach((input, day) => {
    list.append(dayRow(day));
    input.addEventListener("change", () => {
      week[day] = parseRanges(input.value);
      renderDay(day);
    });
  });
  week.forEach((_ranges, day) => renderDay(day));

  editor.hidden = false;
  textEditor.open = false;
})();

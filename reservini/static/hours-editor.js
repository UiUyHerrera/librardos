(() => {
  const editor = document.querySelector("[data-hours-editor]");
  if (!editor) {
    return;
  }

  const STEP = 30;
  const LAST_MINUTE = 23 * 60 + 30;
  const ROW_HEIGHT = 18;
  const RANGE = /^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$/;

  const grid = editor.querySelector("[data-hours-grid]");
  const textEditor = document.querySelector("[data-hours-text]");
  const inputs = [...document.querySelectorAll('input[name^="hours-"]')];
  const dayNames = inputs.map((input) => document.querySelector(`label[for="${input.id}"]`).textContent.trim());
  const week = inputs.map((input) => parseRanges(input.value));
  const columns = [];
  let drag = null;

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

  function formatRange(range) {
    return `${formatTime(range.start)}-${formatTime(range.end)}`;
  }

  function merge(ranges) {
    const sorted = [...ranges].sort((first, second) => first.start - second.start);
    return sorted.reduce((merged, range) => {
      const last = merged[merged.length - 1];
      if (last && range.start <= last.end) {
        last.end = Math.max(last.end, range.end);
      } else {
        merged.push({ ...range });
      }
      return merged;
    }, []);
  }

  function save(day) {
    week[day] = merge(week[day]);
    inputs[day].value = week[day].map(formatRange).join(", ");
  }

  function minuteAt(column, clientY) {
    const offset = clientY - column.getBoundingClientRect().top;
    const minute = Math.floor(offset / ROW_HEIGHT) * STEP;
    return Math.min(Math.max(minute, 0), LAST_MINUTE - STEP);
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text) {
      node.textContent = text;
    }
    return node;
  }

  function blockElement(day, index, range) {
    const block = element("div", "hours-block");
    block.dataset.index = index;
    block.style.top = `${(range.start / STEP) * ROW_HEIGHT}px`;
    block.style.height = `${((range.end - range.start) / STEP) * ROW_HEIGHT}px`;

    const label = element("span", "hours-block-label");
    label.append(element("span", "", formatTime(range.start)), element("span", "", formatTime(range.end)));
    const remove = element("button", "hours-block-remove", "×");
    remove.type = "button";
    remove.dataset.remove = "";
    remove.setAttribute("aria-label", `${editor.dataset.removeLabel} ${dayNames[day]} ${formatRange(range)}`);
    const handle = element("span", "hours-block-handle");
    handle.dataset.resize = "";

    block.append(label, remove, handle);
    return block;
  }

  function renderDay(day) {
    columns[day].replaceChildren(...week[day].map((range, index) => blockElement(day, index, range)));
  }

  function build() {
    const head = element("div", "hours-head");
    head.append(element("span", "hours-corner"));
    dayNames.forEach((name) => head.append(element("span", "hours-day-name", name.slice(0, 3))));

    const body = element("div", "hours-body");
    const times = element("div", "hours-times");
    for (let minute = 0; minute < LAST_MINUTE; minute += 60) {
      const label = element("span", "hours-time", formatTime(minute));
      label.style.top = `${(minute / STEP) * ROW_HEIGHT}px`;
      times.append(label);
    }
    body.append(times);

    dayNames.forEach((_name, day) => {
      const column = element("div", "hours-day");
      column.dataset.day = day;
      column.style.height = `${(LAST_MINUTE / STEP) * ROW_HEIGHT}px`;
      columns.push(column);
      body.append(column);
    });

    const scroller = element("div", "hours-scroll");
    scroller.append(head, body);
    grid.replaceChildren(scroller);
    week.forEach((_ranges, day) => renderDay(day));
    scroller.scrollTop = (7 * 60 / STEP) * ROW_HEIGHT;
  }

  grid.addEventListener("pointerdown", (event) => {
    const column = event.target.closest(".hours-day");
    if (!column || event.target.closest("[data-remove]")) {
      return;
    }

    const day = Number(column.dataset.day);
    const minute = minuteAt(column, event.clientY);
    const block = event.target.closest(".hours-block");

    if (block) {
      const range = week[day][Number(block.dataset.index)];
      const mode = event.target.closest("[data-resize]") ? "resize" : "move";
      drag = { day, column, range, mode, offset: minute - range.start };
    } else {
      const range = { start: minute, end: minute + STEP };
      week[day].push(range);
      drag = { day, column, range, mode: "create", anchor: minute };
      renderDay(day);
    }

    column.setPointerCapture(event.pointerId);
    event.preventDefault();
  });

  grid.addEventListener("pointermove", (event) => {
    if (!drag) {
      return;
    }

    const minute = minuteAt(drag.column, event.clientY);
    const { range } = drag;

    if (drag.mode === "create") {
      range.start = Math.min(drag.anchor, minute);
      range.end = Math.max(drag.anchor, minute) + STEP;
    } else if (drag.mode === "resize") {
      range.end = Math.max(range.start + STEP, minute + STEP);
    } else {
      const length = range.end - range.start;
      range.start = Math.min(Math.max(minute - drag.offset, 0), LAST_MINUTE - length);
      range.end = range.start + length;
    }

    renderDay(drag.day);
  });

  function finishDrag() {
    if (!drag) {
      return;
    }
    save(drag.day);
    renderDay(drag.day);
    drag = null;
  }

  grid.addEventListener("pointerup", finishDrag);
  grid.addEventListener("pointercancel", finishDrag);

  grid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button) {
      return;
    }
    const day = Number(button.closest(".hours-day").dataset.day);
    week[day].splice(Number(button.closest(".hours-block").dataset.index), 1);
    save(day);
    renderDay(day);
  });

  inputs.forEach((input, day) => {
    input.addEventListener("change", () => {
      week[day] = parseRanges(input.value);
      renderDay(day);
    });
  });

  editor.hidden = false;
  textEditor.open = false;
  build();
})();

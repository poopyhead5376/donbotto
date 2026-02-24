const clockEl = document.getElementById("clock");
const hourHand = document.getElementById("hourHand");
const minuteHand = document.getElementById("minuteHand");
const consoleEl = document.getElementById("console");

const logs = [
  "Waiting for user goal...",
  "LLM: 'Open browser and search Linux xdotool docs'",
  "xdotool mousemove 320 220 && xdotool click 1",
  "Window focus adjusted, continuing...",
];

const actionToMessage = {
  "open-terminal": "xdotool key super && xdotool type 'terminal' && xdotool key Return",
  "type-command": "xdotool type --delay 15 'sudo apt install xdotool'",
  "run-sequence": "xdotool key alt+Tab && xdotool key ctrl+l && xdotool type 'https://ollama.com'",
};

function renderClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  clockEl.textContent = `${hh}:${mm}`;

  const minuteDeg = now.getMinutes() * 6;
  const hourDeg = (now.getHours() % 12) * 30 + now.getMinutes() * 0.5;
  hourHand.style.transform = `translateX(-50%) rotate(${hourDeg}deg)`;
  minuteHand.style.transform = `translateX(-50%) rotate(${minuteDeg}deg)`;
}

function appendLog(message) {
  const p = document.createElement("p");
  p.textContent = message;
  consoleEl.appendChild(p);
}

for (const entry of logs) {
  appendLog(entry);
}

document.querySelectorAll("button").forEach((button) => {
  button.addEventListener("click", () => {
    const key = button.dataset.action;
    appendLog(`> ${actionToMessage[key]}`);
  });
});

renderClock();
setInterval(renderClock, 1000);

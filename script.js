const clock = document.getElementById("clock");
const minuteHand = document.querySelector(".minute");
const hourHand = document.querySelector(".hour");

function updateClock() {
  const now = new Date();
  const hours = now.getHours();
  const minutes = now.getMinutes();

  clock.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const minuteDegrees = minutes * 6;
  const hourDegrees = (hours % 12) * 30 + minutes * 0.5;

  minuteHand.style.transform = `translateX(-50%) rotate(${minuteDegrees}deg)`;
  hourHand.style.transform = `translateX(-50%) rotate(${hourDegrees}deg)`;
}

updateClock();
setInterval(updateClock, 1000);

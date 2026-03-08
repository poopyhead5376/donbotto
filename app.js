const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const romInput = document.getElementById("rom-input");
const romStatus = document.getElementById("rom-status");

const world = {
  gravity: 0.55,
  friction: 0.9,
  maxX: 5000,
  floorY: canvas.height - 70,
  goalX: 4720,
};

const baseBlocks = [
  { x: 400, y: 420, w: 110, h: 24 },
  { x: 680, y: 360, w: 120, h: 24 },
  { x: 960, y: 300, w: 140, h: 24 },
  { x: 1320, y: 430, w: 160, h: 24 },
  { x: 1680, y: 370, w: 160, h: 24 },
  { x: 2040, y: 320, w: 200, h: 24 },
  { x: 2500, y: 390, w: 180, h: 24 },
  { x: 2920, y: 340, w: 170, h: 24 },
  { x: 3360, y: 280, w: 180, h: 24 },
  { x: 3780, y: 410, w: 210, h: 24 },
  { x: 4180, y: 350, w: 160, h: 24 },
];

let blocks = structuredClone(baseBlocks);
let randomFn = Math.random;
let loadedRomInfo = null;

function mulberry32(seed) {
  let t = seed >>> 0;
  return function seededRandom() {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function fnv1a(bytes) {
  let hash = 2166136261;
  for (const byte of bytes) {
    hash ^= byte;
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function readAscii(bytes, start, end) {
  const chars = [];
  for (let i = start; i < end; i += 1) {
    const code = bytes[i];
    if (!code) continue;
    const ch = String.fromCharCode(code);
    if (/^[A-Za-z0-9 !._-]$/.test(ch)) chars.push(ch);
  }
  return chars.join("").trim();
}

function isLikelyGbaRom(bytes) {
  if (bytes.length < 0xc0) return false;
  const signature = String.fromCharCode(bytes[0xac], bytes[0xad], bytes[0xae]);
  const hasNintendoMark = signature === "AGB";
  const hasGoodSize = bytes.length > 1024 * 128;
  return hasNintendoMark || hasGoodSize;
}

function applyRomFlavor(seed) {
  const seeded = mulberry32(seed);
  randomFn = seeded;
  blocks = baseBlocks.map((block) => ({
    ...block,
    y: Math.max(210, Math.min(world.floorY - 34, block.y + Math.round((seeded() - 0.5) * 40))),
  }));
}

function createMario(index) {
  const lane = index % 10;
  return {
    x: 40 + (index % 5) * 10,
    y: world.floorY - 28 - lane * 3,
    w: 14,
    h: 22,
    vx: 0,
    vy: 0,
    onGround: false,
    reached: false,
    color: `hsl(${(index * 37) % 360} 80% 60%)`,
    ai: {
      speed: 2.1 + randomFn() * 1.4,
      jumpStrength: 10 + randomFn() * 3,
      bravery: randomFn(),
      recovery: 0,
    },
  };
}

let marios = [];
let cameraX = 0;

function reset() {
  marios = Array.from({ length: 50 }, (_, i) => createMario(i));
}

function overlaps(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function applyCollisions(mario) {
  mario.onGround = false;

  if (mario.y + mario.h >= world.floorY) {
    mario.y = world.floorY - mario.h;
    mario.vy = 0;
    mario.onGround = true;
  }

  for (const block of blocks) {
    if (!overlaps(mario, block)) continue;

    const prevBottom = mario.y + mario.h - mario.vy;
    const prevTop = mario.y - mario.vy;

    if (prevBottom <= block.y) {
      mario.y = block.y - mario.h;
      mario.vy = 0;
      mario.onGround = true;
    } else if (prevTop >= block.y + block.h) {
      mario.y = block.y + block.h;
      mario.vy = 0;
    } else if (mario.x + mario.w / 2 < block.x + block.w / 2) {
      mario.x = block.x - mario.w;
      mario.vx *= -0.35;
    } else {
      mario.x = block.x + block.w;
      mario.vx *= -0.35;
    }
  }

  if (mario.x < 0) {
    mario.x = 0;
    mario.vx = 0;
  }
  if (mario.x > world.maxX) {
    mario.x = world.maxX;
    mario.vx = 0;
  }
}

function aiStep(mario) {
  if (mario.reached) return;

  const forwardSpeed = mario.ai.speed * (0.9 + randomFn() * 0.2);
  mario.vx += 0.14;
  if (mario.vx > forwardSpeed) mario.vx = forwardSpeed;

  const upcoming = blocks.find(
    (b) => b.x > mario.x && b.x - mario.x < 35 && mario.y + mario.h > b.y - 12,
  );

  const riskJump = randomFn() < 0.006 + mario.ai.bravery * 0.01;

  if (mario.onGround && (upcoming || riskJump || mario.ai.recovery > 30)) {
    mario.vy = -mario.ai.jumpStrength;
    mario.ai.recovery = 0;
  } else {
    mario.ai.recovery += 1;
  }

  mario.vy += world.gravity;
  mario.x += mario.vx;
  mario.y += mario.vy;
  mario.vx *= world.friction;

  applyCollisions(mario);

  if (mario.x >= world.goalX) {
    mario.reached = true;
    mario.vx = 0;
  }
}

function drawWorld() {
  ctx.save();
  ctx.translate(-cameraX, 0);

  ctx.fillStyle = "#8bd3ff";
  ctx.fillRect(cameraX, 0, canvas.width, canvas.height);

  ctx.fillStyle = "#76c96a";
  ctx.fillRect(0, world.floorY, world.maxX + 120, canvas.height - world.floorY);

  ctx.fillStyle = "#6f4b2a";
  for (const block of blocks) {
    ctx.fillRect(block.x, block.y, block.w, block.h);
    ctx.strokeStyle = "rgba(0,0,0,0.2)";
    ctx.strokeRect(block.x + 0.5, block.y + 0.5, block.w - 1, block.h - 1);
  }

  ctx.fillStyle = "#ffd861";
  ctx.fillRect(world.goalX + 20, world.floorY - 130, 6, 130);
  ctx.fillStyle = "#ff4d6d";
  ctx.beginPath();
  ctx.moveTo(world.goalX + 26, world.floorY - 130);
  ctx.lineTo(world.goalX + 90, world.floorY - 104);
  ctx.lineTo(world.goalX + 26, world.floorY - 84);
  ctx.closePath();
  ctx.fill();

  for (const mario of marios) {
    ctx.fillStyle = mario.reached ? "#fff" : mario.color;
    ctx.fillRect(mario.x, mario.y, mario.w, mario.h);
    ctx.fillStyle = "#d8342a";
    ctx.fillRect(mario.x, mario.y, mario.w, 7);
    ctx.fillStyle = "#1f1f1f";
    ctx.fillRect(mario.x + 2, mario.y + mario.h, 4, 2);
    ctx.fillRect(mario.x + 8, mario.y + mario.h, 4, 2);
  }

  ctx.restore();
}

function updateHud() {
  const finished = marios.filter((m) => m.reached).length;
  const avg =
    marios.reduce((sum, mario) => sum + Math.min(mario.x / world.goalX, 1), 0) / marios.length;

  document.getElementById("goal-count").textContent = String(finished);
  document.getElementById("avg-progress").textContent = `${Math.round(avg * 100)}%`;
}

async function handleRomFile() {
  const [file] = romInput.files || [];
  if (!file) {
    loadedRomInfo = null;
    blocks = structuredClone(baseBlocks);
    randomFn = Math.random;
    romStatus.textContent = "No ROM loaded.";
    reset();
    return;
  }

  romStatus.textContent = `Reading ${file.name}...`;

  try {
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (!isLikelyGbaRom(bytes)) {
      romStatus.textContent = "This file does not look like a GBA ROM. Try a .gba dump.";
      return;
    }

    const hash = fnv1a(bytes);
    const title = readAscii(bytes, 0xa0, 0xac) || "Unknown Title";
    const gameCode = readAscii(bytes, 0xac, 0xb0) || "----";

    loadedRomInfo = {
      name: file.name,
      size: bytes.length,
      title,
      gameCode,
      hash,
    };

    applyRomFlavor(hash);
    reset();

    romStatus.textContent = `ROM loaded: ${loadedRomInfo.title} (${loadedRomInfo.gameCode}) • ${(loadedRomInfo.size / (1024 * 1024)).toFixed(2)} MB`;
  } catch (error) {
    romStatus.textContent = `Failed to read file: ${error instanceof Error ? error.message : "unknown error"}`;
  }
}

function tick() {
  for (const mario of marios) aiStep(mario);

  const leaderX = marios.reduce((best, mario) => Math.max(best, mario.x), 0);
  cameraX = Math.max(0, Math.min(leaderX - canvas.width * 0.3, world.maxX - canvas.width + 120));

  drawWorld();
  updateHud();
  requestAnimationFrame(tick);
}

romInput.addEventListener("change", () => {
  handleRomFile();
});

window.addEventListener("keydown", (event) => {
  if (event.key.toLowerCase() === "r") reset();
});

reset();
tick();

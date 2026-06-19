(() => {
  const canvas = document.getElementById("gameCanvas");
  const ctx = canvas.getContext("2d");
  const scoreEl = document.getElementById("score");
  const bestEl = document.getElementById("best");
  const coinsEl = document.getElementById("coins");
  const menu = document.getElementById("menu");
  const menuTitle = document.getElementById("menuTitle");
  const menuStats = document.getElementById("menuStats");
  const playBtn = document.getElementById("playBtn");
  const reviveBtn = document.getElementById("reviveBtn");
  const adPanel = document.getElementById("adPanel");
  const adText = document.getElementById("adText");

  const cfg = window.COLOR_GATE_RUNNER_CONFIG || {};
  const colors = [
    { name: "mint", fill: "#34d399", dark: "#0f766e" },
    { name: "blue", fill: "#60a5fa", dark: "#1d4ed8" },
    { name: "amber", fill: "#f59e0b", dark: "#b45309" },
    { name: "rose", fill: "#fb7185", dark: "#be123c" }
  ];

  const store = {
    best: Number(localStorage.getItem("cgr_best") || 0),
    coins: Number(localStorage.getItem("cgr_coins") || 0),
    runs: Number(localStorage.getItem("cgr_runs") || 0)
  };

  const game = {
    state: "menu",
    width: 900,
    height: 1600,
    dpr: 1,
    last: 0,
    score: 0,
    runCoins: 0,
    distance: 0,
    speed: 720,
    spawnY: -260,
    gateTimer: 0,
    coinTimer: 0,
    shake: 0,
    revived: false,
    pointerActive: false,
    player: {
      x: 450,
      y: 1240,
      r: 42,
      targetX: 450,
      colorIndex: 0,
      invincible: 0
    },
    gates: [],
    coins: [],
    particles: []
  };

  function postEvent(event, params = {}) {
    if (!cfg.analyticsUrl) return;
    let visitorId = "";
    try {
      visitorId = window.localStorage.getItem("careersdna_vid") || "";
      if (!visitorId) {
        visitorId = (window.crypto && window.crypto.randomUUID)
          ? window.crypto.randomUUID()
          : String(Date.now()) + Math.random().toString(16).slice(2);
        window.localStorage.setItem("careersdna_vid", visitorId);
      }
      if (!window.sessionStorage.getItem("careersdna_landing_path")) {
        window.sessionStorage.setItem("careersdna_landing_path", window.location.pathname);
        window.sessionStorage.setItem("careersdna_landing_referrer", document.referrer || "");
      }
    } catch {}
    fetch(cfg.analyticsUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event,
        visitor_id: visitorId,
        params: {
          page_path: "/games/color-gate-runner",
          page_type: "game",
          landing_path: (() => {
            try { return window.sessionStorage.getItem("careersdna_landing_path") || "/games/color-gate-runner"; } catch { return "/games/color-gate-runner"; }
          })(),
          landing_referrer: (() => {
            try { return window.sessionStorage.getItem("careersdna_landing_referrer") || ""; } catch { return ""; }
          })(),
          referrer: document.referrer || "",
          ...params
        }
      }),
      keepalive: true
    }).catch(() => {});
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    game.dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.floor(rect.width * game.dpr));
    canvas.height = Math.max(1, Math.floor(rect.height * game.dpr));
    ctx.setTransform(game.dpr, 0, 0, game.dpr, 0, 0);
    game.width = rect.width;
    game.height = rect.height;
    game.player.y = game.height * 0.77;
    game.player.r = Math.max(24, Math.min(42, game.width * 0.082));
    game.player.x = clamp(game.player.x, 46, game.width - 46);
    game.player.targetX = clamp(game.player.targetX, 46, game.width - 46);
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function rand(min, max) {
    return min + Math.random() * (max - min);
  }

  function chooseColor(except = -1) {
    let next = Math.floor(Math.random() * colors.length);
    if (next === except) next = (next + 1 + Math.floor(Math.random() * (colors.length - 1))) % colors.length;
    return next;
  }

  function resetRun() {
    game.state = "playing";
    game.last = performance.now();
    game.score = 0;
    game.runCoins = 0;
    game.distance = 0;
    game.speed = 620;
    game.gateTimer = 0.15;
    game.coinTimer = 0.45;
    game.shake = 0;
    game.revived = false;
    game.gates = [];
    game.coins = [];
    game.particles = [];
    game.player.x = game.width / 2;
    game.player.targetX = game.width / 2;
    game.player.colorIndex = chooseColor();
    game.player.invincible = 1.2;
    menu.classList.add("is-hidden");
    reviveBtn.hidden = true;
    adPanel.hidden = true;
    postEvent("game_start");
  }

  function reviveRun() {
    game.state = "playing";
    game.last = performance.now();
    game.revived = true;
    game.player.invincible = 2.25;
    game.gates = game.gates.filter((gate) => gate.y < game.player.y - 120 || gate.y > game.player.y + 160);
    menu.classList.add("is-hidden");
    reviveBtn.hidden = true;
    showRewardedAd();
    postEvent("game_revive", { score: Math.floor(game.score) });
  }

  function endRun() {
    game.state = "ended";
    store.runs += 1;
    store.best = Math.max(store.best, Math.floor(game.score));
    store.coins += game.runCoins;
    localStorage.setItem("cgr_best", String(store.best));
    localStorage.setItem("cgr_coins", String(store.coins));
    localStorage.setItem("cgr_runs", String(store.runs));
    syncHud();

    menuTitle.textContent = "Run Ended";
    menuStats.textContent = `Score ${Math.floor(game.score)} · Best ${store.best}`;
    playBtn.textContent = "Retry";
    reviveBtn.hidden = game.revived || Math.floor(game.score) < 80;
    menu.classList.remove("is-hidden");
    postEvent("game_end", {
      score: Math.floor(game.score),
      coins: game.runCoins,
      best: store.best,
      run_index: store.runs
    });
    if (store.runs % 3 === 0) showInterstitialAd();
  }

  function syncHud() {
    scoreEl.textContent = String(Math.floor(game.score));
    bestEl.textContent = String(store.best);
    coinsEl.textContent = String(store.coins + game.runCoins);
  }

  function showInterstitialAd() {
    if (!cfg.enableMockAds) return;
    adText.textContent = "Interstitial slot";
    adPanel.hidden = false;
    window.setTimeout(() => {
      adPanel.hidden = true;
    }, 1500);
  }

  function showRewardedAd() {
    if (!cfg.enableMockAds) return;
    adText.textContent = "Rewarded slot";
    adPanel.hidden = false;
    window.setTimeout(() => {
      adPanel.hidden = true;
    }, 1200);
  }

  function spawnGate() {
    const lanes = 3;
    const gap = game.width / lanes;
    const safeLane = Math.floor(Math.random() * lanes);
    const gateColor = Math.random() < 0.72 ? game.player.colorIndex : chooseColor(game.player.colorIndex);
    const width = Math.max(74, game.width * 0.22);
    const y = -100;
    for (let lane = 0; lane < lanes; lane += 1) {
      if (lane === safeLane && Math.random() < 0.38) continue;
      const colorIndex = lane === safeLane ? gateColor : chooseColor(gateColor);
      game.gates.push({
        x: gap * lane + gap / 2,
        y,
        w: width,
        h: 70,
        colorIndex,
        hit: false
      });
    }
  }

  function spawnCoins() {
    const count = Math.random() < 0.45 ? 3 : 2;
    const startX = rand(game.width * 0.22, game.width * 0.78);
    for (let i = 0; i < count; i += 1) {
      game.coins.push({
        x: clamp(startX + (i - 1) * 42, 36, game.width - 36),
        y: -70 - i * 48,
        r: 12,
        taken: false
      });
    }
  }

  function burst(x, y, color, count = 12) {
    for (let i = 0; i < count; i += 1) {
      game.particles.push({
        x,
        y,
        vx: rand(-190, 190),
        vy: rand(-260, 110),
        life: rand(0.22, 0.48),
        maxLife: 0.48,
        color
      });
    }
  }

  function update(dt) {
    if (game.state !== "playing") return;

    game.distance += game.speed * dt;
    game.score += dt * (12 + game.speed * 0.018);
    game.speed = Math.min(1120, game.speed + dt * 16);
    game.player.invincible = Math.max(0, game.player.invincible - dt);
    game.shake = Math.max(0, game.shake - dt * 6);
    game.player.x += (game.player.targetX - game.player.x) * Math.min(1, dt * 14);

    game.gateTimer -= dt;
    if (game.gateTimer <= 0) {
      spawnGate();
      game.gateTimer = rand(0.62, 0.92) * (820 / game.speed);
    }

    game.coinTimer -= dt;
    if (game.coinTimer <= 0) {
      spawnCoins();
      game.coinTimer = rand(0.78, 1.25);
    }

    for (const gate of game.gates) {
      gate.y += game.speed * dt;
      if (!gate.hit && circleRect(game.player.x, game.player.y, game.player.r * 0.76, gate)) {
        gate.hit = true;
        if (gate.colorIndex === game.player.colorIndex || game.player.invincible > 0) {
          game.score += 35;
          game.player.colorIndex = gate.colorIndex;
          burst(gate.x, gate.y, colors[gate.colorIndex].fill, 10);
        } else {
          game.shake = 1;
          burst(game.player.x, game.player.y, "#f6f2e8", 22);
          endRun();
          return;
        }
      }
    }

    for (const coin of game.coins) {
      coin.y += game.speed * dt;
      if (!coin.taken && dist(game.player.x, game.player.y, coin.x, coin.y) < game.player.r + coin.r) {
        coin.taken = true;
        game.runCoins += 1;
        game.score += 10;
        burst(coin.x, coin.y, "#facc15", 8);
      }
    }

    for (const p of game.particles) {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += 540 * dt;
      p.life -= dt;
    }

    game.gates = game.gates.filter((gate) => gate.y < game.height + 120 && !gate.hit);
    game.coins = game.coins.filter((coin) => coin.y < game.height + 80 && !coin.taken);
    game.particles = game.particles.filter((p) => p.life > 0);
    syncHud();
  }

  function circleRect(cx, cy, cr, rect) {
    const rx = clamp(cx, rect.x - rect.w / 2, rect.x + rect.w / 2);
    const ry = clamp(cy, rect.y - rect.h / 2, rect.y + rect.h / 2);
    return dist(cx, cy, rx, ry) < cr;
  }

  function dist(ax, ay, bx, by) {
    return Math.hypot(ax - bx, ay - by);
  }

  function drawTrack() {
    const w = game.width;
    const h = game.height;
    const laneW = w / 3;
    ctx.fillStyle = "#101114";
    ctx.fillRect(0, 0, w, h);

    const sky = ctx.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, "#20232a");
    sky.addColorStop(0.56, "#121418");
    sky.addColorStop(1, "#08090b");
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, h);

    const offset = (game.distance * 0.12) % 90;
    for (let i = -1; i < h / 90 + 2; i += 1) {
      const y = i * 90 + offset;
      ctx.fillStyle = "rgba(255,255,255,0.055)";
      ctx.fillRect(w * 0.12, y, w * 0.76, 2);
    }

    ctx.strokeStyle = "rgba(255,255,255,0.13)";
    ctx.lineWidth = 2;
    for (let i = 1; i < 3; i += 1) {
      const x = laneW * i;
      ctx.setLineDash([18, 24]);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    const vignette = ctx.createRadialGradient(w / 2, h * 0.48, h * 0.1, w / 2, h * 0.5, h * 0.72);
    vignette.addColorStop(0, "rgba(255,255,255,0)");
    vignette.addColorStop(1, "rgba(0,0,0,0.48)");
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, w, h);
  }

  function roundRect(x, y, w, h, r) {
    const radius = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + w, y, x + w, y + h, radius);
    ctx.arcTo(x + w, y + h, x, y + h, radius);
    ctx.arcTo(x, y + h, x, y, radius);
    ctx.arcTo(x, y, x + w, y, radius);
    ctx.closePath();
  }

  function drawGate(gate) {
    const c = colors[gate.colorIndex];
    ctx.save();
    ctx.shadowBlur = 22;
    ctx.shadowColor = c.fill;
    roundRect(gate.x - gate.w / 2, gate.y - gate.h / 2, gate.w, gate.h, 14);
    ctx.fillStyle = c.fill;
    ctx.fill();
    ctx.shadowBlur = 0;
    roundRect(gate.x - gate.w / 2 + 8, gate.y - gate.h / 2 + 8, gate.w - 16, gate.h - 16, 10);
    ctx.fillStyle = c.dark;
    ctx.globalAlpha = 0.58;
    ctx.fill();
    ctx.restore();
  }

  function drawCoin(coin) {
    ctx.save();
    ctx.translate(coin.x, coin.y);
    ctx.fillStyle = "#facc15";
    ctx.shadowColor = "#facc15";
    ctx.shadowBlur = 14;
    ctx.beginPath();
    ctx.arc(0, 0, coin.r, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = "#854d0e";
    ctx.fillRect(-2, -7, 4, 14);
    ctx.restore();
  }

  function drawPlayer() {
    const p = game.player;
    const c = colors[p.colorIndex];
    ctx.save();
    ctx.translate(p.x, p.y);
    if (p.invincible > 0) {
      ctx.globalAlpha = 0.24 + Math.sin(performance.now() * 0.018) * 0.08;
      ctx.strokeStyle = "#f6f2e8";
      ctx.lineWidth = 6;
      ctx.beginPath();
      ctx.arc(0, 0, p.r + 16, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    ctx.shadowBlur = 26;
    ctx.shadowColor = c.fill;
    ctx.fillStyle = c.fill;
    ctx.beginPath();
    ctx.arc(0, 0, p.r, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = "rgba(255,255,255,0.76)";
    ctx.beginPath();
    ctx.arc(-p.r * 0.28, -p.r * 0.3, p.r * 0.22, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function drawParticles() {
    for (const p of game.particles) {
      ctx.globalAlpha = Math.max(0, p.life / p.maxLife);
      ctx.fillStyle = p.color;
      ctx.fillRect(p.x - 3, p.y - 3, 6, 6);
    }
    ctx.globalAlpha = 1;
  }

  function render() {
    ctx.save();
    if (game.shake > 0) {
      ctx.translate(rand(-8, 8) * game.shake, rand(-8, 8) * game.shake);
    }
    drawTrack();
    for (const coin of game.coins) drawCoin(coin);
    for (const gate of game.gates) drawGate(gate);
    drawParticles();
    drawPlayer();
    ctx.restore();
  }

  function loop(now) {
    const dt = Math.min(0.033, (now - game.last) / 1000 || 0);
    game.last = now;
    update(dt);
    render();
    requestAnimationFrame(loop);
  }

  function setTargetFromClientX(clientX) {
    const rect = canvas.getBoundingClientRect();
    game.player.targetX = clamp(clientX - rect.left, game.player.r + 8, game.width - game.player.r - 8);
  }

  canvas.addEventListener("pointerdown", (event) => {
    game.pointerActive = true;
    canvas.setPointerCapture(event.pointerId);
    setTargetFromClientX(event.clientX);
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!game.pointerActive) return;
    setTargetFromClientX(event.clientX);
  });

  canvas.addEventListener("pointerup", () => {
    game.pointerActive = false;
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft" || event.key.toLowerCase() === "a") {
      game.player.targetX = clamp(game.player.targetX - game.width / 3, game.player.r + 8, game.width - game.player.r - 8);
    }
    if (event.key === "ArrowRight" || event.key.toLowerCase() === "d") {
      game.player.targetX = clamp(game.player.targetX + game.width / 3, game.player.r + 8, game.width - game.player.r - 8);
    }
    if ((event.key === " " || event.key === "Enter") && game.state !== "playing") {
      resetRun();
    }
  });

  playBtn.addEventListener("click", resetRun);
  reviveBtn.addEventListener("click", reviveRun);
  window.addEventListener("resize", resize);

  function boot() {
    resize();
    syncHud();
    menuStats.textContent = `Best ${store.best}`;
    game.last = performance.now();
    postEvent("page_view_custom", { page_type: "game" });
    requestAnimationFrame(loop);
    postEvent("game_view");
  }

  boot();
})();

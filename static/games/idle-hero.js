(() => {
  const cfg = window.IDLE_HERO_CONFIG || {};
  const els = {
    level: document.getElementById("levelText"),
    gold: document.getElementById("goldText"),
    power: document.getElementById("powerText"),
    stage: document.getElementById("stageText"),
    enemyName: document.getElementById("enemyName"),
    enemy: document.getElementById("enemy"),
    skillRing: document.getElementById("skillRing"),
    damageStack: document.getElementById("damageStack"),
    hpFill: document.getElementById("hpFill"),
    expText: document.getElementById("expText"),
    expFill: document.getElementById("expFill"),
    status: document.getElementById("statusText"),
    swordCost: document.getElementById("swordCost"),
    skillCost: document.getElementById("skillCost"),
    upgradeSword: document.getElementById("upgradeSword"),
    upgradeSkill: document.getElementById("upgradeSkill"),
    claimLogin: document.getElementById("claimLogin"),
    boostAd: document.getElementById("boostAd"),
    strike: document.getElementById("strikeBtn"),
    offlineModal: document.getElementById("offlineModal"),
    offlineText: document.getElementById("offlineText"),
    claimOffline: document.getElementById("claimOffline"),
    claimOfflineDouble: document.getElementById("claimOfflineDouble"),
    adToast: document.getElementById("adToast"),
    adToastText: document.getElementById("adToastText")
  };

  const enemyNames = [
    "Training Slime",
    "Copper Imp",
    "Clockwork Beetle",
    "Neon Wraith",
    "Iron Golem",
    "Void Captain",
    "Solar Drake"
  ];

  const defaultState = {
    level: 1,
    exp: 0,
    gold: 0,
    stage: 1,
    sword: 1,
    skill: 1,
    kills: 0,
    enemyHp: 0,
    enemyMaxHp: 0,
    boostUntil: 0,
    lastSeen: Date.now(),
    lastLoginDay: "",
    loginStreak: 0
  };

  let state = loadState();
  let pendingOffline = null;
  let lastTick = performance.now();
  let attackTimer = 0;
  let saveTimer = 0;
  let nativeAdsReady = false;

  function loadState() {
    try {
      return { ...defaultState, ...JSON.parse(localStorage.getItem("idle_hero_state") || "{}") };
    } catch {
      return { ...defaultState };
    }
  }

  function saveState() {
    state.lastSeen = Date.now();
    localStorage.setItem("idle_hero_state", JSON.stringify(state));
  }

  function postEvent(event, params = {}) {
    if (!cfg.analyticsUrl) return;
    fetch(cfg.analyticsUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event,
        params: {
          page_path: "/games/idle-hero",
          page_type: "game",
          ...params
        }
      }),
      keepalive: true
    }).catch(() => {});
  }

  async function initNativeAds() {
    const admob = window.Capacitor?.Plugins?.AdMob;
    if (!admob) return;
    try {
      await admob.initialize();
      nativeAdsReady = true;
    } catch {
      nativeAdsReady = false;
    }
  }

  function fmt(n) {
    if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 10_000) return `${Math.floor(n / 1000)}K`;
    return String(Math.floor(n));
  }

  function todayKey() {
    return new Date().toISOString().slice(0, 10);
  }

  function power() {
    const base = 8 + state.level * 3;
    return Math.floor(base * Math.pow(1.34, state.sword - 1) * (1 + state.skill * 0.08));
  }

  function dps() {
    const boost = Date.now() < state.boostUntil ? 2 : 1;
    return power() * (0.85 + state.skill * 0.08) * boost;
  }

  function expNeed() {
    return Math.floor(20 * Math.pow(1.24, state.level - 1));
  }

  function enemyMaxHp() {
    return Math.floor(54 * Math.pow(1.2, state.stage - 1) * (1 + Math.floor(state.stage / 5) * 0.16));
  }

  function goldReward() {
    return Math.floor(7 * Math.pow(1.16, state.stage - 1) * (1 + state.level * 0.035));
  }

  function expReward() {
    return Math.floor(6 + state.stage * 1.6);
  }

  function swordCost() {
    return Math.floor(24 * Math.pow(1.42, state.sword - 1));
  }

  function skillCost() {
    return Math.floor(60 * Math.pow(1.55, state.skill - 1));
  }

  function ensureEnemy() {
    if (!state.enemyMaxHp || state.enemyHp <= 0) {
      state.enemyMaxHp = enemyMaxHp();
      state.enemyHp = state.enemyMaxHp;
    }
  }

  function grantExp(amount) {
    state.exp += amount;
    let need = expNeed();
    while (state.exp >= need) {
      state.exp -= need;
      state.level += 1;
      status(`Level up. Skill effects expanded.`);
      castSkill(true);
      need = expNeed();
    }
  }

  function killEnemy() {
    state.kills += 1;
    state.gold += goldReward();
    grantExp(expReward());
    if (state.kills % 4 === 0) state.stage += 1;
    state.enemyMaxHp = enemyMaxHp();
    state.enemyHp = state.enemyMaxHp;
    status(`Stage ${state.stage} cleared reward gained.`);
    postEvent("idle_enemy_kill", { stage: state.stage, level: state.level, kills: state.kills });
  }

  function hit(multiplier = 1, manual = false) {
    ensureEnemy();
    const dmg = Math.max(1, Math.floor(power() * multiplier * (Date.now() < state.boostUntil ? 2 : 1)));
    state.enemyHp -= dmg;
    showDamage(dmg, manual);
    castSkill(false);
    if (state.enemyHp <= 0) killEnemy();
    render();
  }

  function showDamage(dmg, manual) {
    const item = document.createElement("div");
    item.className = "damage";
    item.textContent = fmt(dmg);
    item.style.fontSize = `${Math.min(52, 21 + state.skill * 1.8 + state.level * 0.15)}px`;
    item.style.setProperty("--dx", `${Math.round((Math.random() - 0.5) * 76)}px`);
    if (manual) item.style.color = "#f8f5ec";
    els.damageStack.appendChild(item);
    window.setTimeout(() => item.remove(), 820);
    els.enemy.classList.add("is-hit");
    window.setTimeout(() => els.enemy.classList.remove("is-hit"), 120);
  }

  function castSkill(levelUp) {
    const scale = Math.min(5.8, 1.55 + state.skill * 0.18 + state.level * 0.025 + (levelUp ? 0.8 : 0));
    els.skillRing.style.setProperty("--skill-scale", scale.toFixed(2));
    els.skillRing.classList.remove("cast");
    void els.skillRing.offsetWidth;
    els.skillRing.classList.add("cast");
  }

  function status(text) {
    els.status.textContent = text;
  }

  function render() {
    ensureEnemy();
    const need = expNeed();
    const hpRatio = Math.max(0, state.enemyHp / state.enemyMaxHp);
    const expRatio = Math.max(0, Math.min(1, state.exp / need));
    const boostActive = Date.now() < state.boostUntil;

    els.level.textContent = fmt(state.level);
    els.gold.textContent = fmt(state.gold);
    els.power.textContent = fmt(power());
    els.stage.textContent = `Stage ${state.stage}`;
    els.enemyName.textContent = enemyNames[(state.stage - 1) % enemyNames.length];
    els.hpFill.style.width = `${hpRatio * 100}%`;
    els.expFill.style.width = `${expRatio * 100}%`;
    els.expText.textContent = `${fmt(state.exp)} / ${fmt(need)}`;
    els.swordCost.textContent = fmt(swordCost());
    els.skillCost.textContent = fmt(skillCost());
    els.upgradeSword.disabled = state.gold < swordCost();
    els.upgradeSkill.disabled = state.gold < skillCost();
    els.boostAd.querySelector("strong").textContent = boostActive ? "ON" : "2x";

    const hue = (state.stage * 34) % 360;
    els.enemy.style.filter = `hue-rotate(${hue}deg)`;
    document.getElementById("heroAura").style.transform = `scale(${Math.min(2.2, 1 + state.level * 0.012 + state.skill * 0.025)})`;
  }

  function upgradeSword() {
    const cost = swordCost();
    if (state.gold < cost) return;
    state.gold -= cost;
    state.sword += 1;
    status(`Sword upgraded to ${state.sword}.`);
    hit(1.8, true);
    postEvent("idle_upgrade", { type: "sword", level: state.sword });
  }

  function upgradeSkill() {
    const cost = skillCost();
    if (state.gold < cost) return;
    state.gold -= cost;
    state.skill += 1;
    status(`Skill upgraded to ${state.skill}.`);
    hit(2.6, true);
    postEvent("idle_upgrade", { type: "skill", level: state.skill });
  }

  function claimLogin() {
    const key = todayKey();
    if (state.lastLoginDay === key) {
      status("Today's login reward already claimed.");
      return;
    }
    state.loginStreak = state.lastLoginDay ? state.loginStreak + 1 : 1;
    state.lastLoginDay = key;
    const rewardGold = Math.floor(80 * Math.pow(1.11, state.level - 1) * (1 + state.loginStreak * 0.08));
    const rewardExp = Math.floor(expNeed() * 0.22);
    state.gold += rewardGold;
    grantExp(rewardExp);
    status(`Login reward: ${fmt(rewardGold)} gold, ${fmt(rewardExp)} EXP.`);
    postEvent("idle_login_claim", { streak: state.loginStreak, gold: rewardGold });
    render();
    saveState();
  }

  async function showAd(label, cb) {
    const admob = window.Capacitor?.Plugins?.AdMob;
    const rewardAdId = cfg.rewardAdId || "ca-app-pub-3940256099942544/5224354917";
    if (nativeAdsReady && admob) {
      try {
        els.adToastText.textContent = "Loading rewarded ad";
        els.adToast.hidden = false;
        await admob.prepareRewardVideoAd({
          adId: rewardAdId,
          isTesting: true,
          immersiveMode: true
        });
        await admob.showRewardVideoAd();
        els.adToast.hidden = true;
        cb();
        return;
      } catch {
        els.adToastText.textContent = "Ad unavailable. Reward granted.";
        window.setTimeout(() => {
          els.adToast.hidden = true;
          cb();
        }, 700);
        return;
      }
    }
    if (!cfg.enableMockAds) {
      cb();
      return;
    }
    els.adToastText.textContent = label;
    els.adToast.hidden = false;
    window.setTimeout(() => {
      els.adToast.hidden = true;
      cb();
    }, 900);
  }

  function activateBoost() {
    showAd("Rewarded ad slot: 2x power", () => {
      state.boostUntil = Date.now() + 1000 * 60 * 3;
      status("2x power active for 3 minutes.");
      postEvent("idle_reward_ad", { reward: "boost" });
      render();
      saveState();
    });
  }

  function calculateOffline() {
    const elapsed = Math.max(0, Math.floor((Date.now() - Number(state.lastSeen || Date.now())) / 1000));
    if (elapsed < 45) return null;
    const capped = Math.min(elapsed, 60 * 60 * 8);
    const kills = Math.floor((dps() * capped * 0.55) / Math.max(1, enemyMaxHp()));
    const gold = Math.max(20, Math.floor(kills * goldReward() + capped * Math.max(1, state.stage * 0.8)));
    const exp = Math.max(8, Math.floor(kills * expReward() + capped * 0.35));
    return { seconds: capped, gold, exp, kills };
  }

  function openOfflineReward(reward) {
    pendingOffline = reward;
    els.offlineText.textContent = `${fmt(reward.gold)} gold and ${fmt(reward.exp)} EXP earned over ${Math.floor(reward.seconds / 60)} minutes.`;
    els.offlineModal.hidden = false;
  }

  function claimOffline(multiplier) {
    if (!pendingOffline) return;
    state.gold += pendingOffline.gold * multiplier;
    grantExp(pendingOffline.exp * multiplier);
    state.kills += pendingOffline.kills * multiplier;
    state.stage += Math.floor((pendingOffline.kills * multiplier) / 4);
    status(`Offline reward claimed: ${fmt(pendingOffline.gold * multiplier)} gold.`);
    postEvent("idle_offline_claim", { multiplier, seconds: pendingOffline.seconds });
    pendingOffline = null;
    els.offlineModal.hidden = true;
    render();
    saveState();
  }

  function tick(now) {
    const dt = Math.min(0.12, (now - lastTick) / 1000 || 0);
    lastTick = now;
    attackTimer -= dt;
    saveTimer += dt;

    if (attackTimer <= 0) {
      hit(0.75 + state.skill * 0.04, false);
      attackTimer = Math.max(0.32, 1.05 - state.skill * 0.018);
    }
    if (saveTimer >= 5) {
      saveTimer = 0;
      saveState();
    }
    requestAnimationFrame(tick);
  }

  els.strike.addEventListener("click", () => hit(1.45, true));
  els.upgradeSword.addEventListener("click", upgradeSword);
  els.upgradeSkill.addEventListener("click", upgradeSkill);
  els.claimLogin.addEventListener("click", claimLogin);
  els.boostAd.addEventListener("click", activateBoost);
  els.claimOffline.addEventListener("click", () => claimOffline(1));
  els.claimOfflineDouble.addEventListener("click", () => {
    showAd("Rewarded ad slot: offline 2x", () => claimOffline(2));
  });

  window.addEventListener("beforeunload", saveState);

  function boot() {
    initNativeAds();
    ensureEnemy();
    const offline = calculateOffline();
    render();
    postEvent("idle_view", { level: state.level, stage: state.stage });
    if (offline) openOfflineReward(offline);
    requestAnimationFrame(tick);
  }

  boot();
})();

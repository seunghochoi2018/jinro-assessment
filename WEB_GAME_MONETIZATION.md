# Web Game Monetization Plan

## Live Paths

- Games index: `/games`
- Idle game: `/games/idle-hero`
- Runner game: `/games/color-gate-runner`

## Revenue Setup

The site already has `ads.txt` for:

- `google.com, pub-6018524927950587, DIRECT, f08c47fec0942fa0`

Set these environment variables on Render when real ad slots are ready:

- `ADSENSE_CLIENT=ca-pub-6018524927950587`
- `ADSENSE_SLOT_GAME_TOP=...`
- `ADSENSE_SLOT_GAME_BOTTOM=...`
- `ADSENSE_SLOT_BOTTOM=...`

For web, use display ads around the game. Do not require users to click or view AdSense ads to receive in-game rewards.

## Traffic Plan

1. Publish `/games/idle-hero`.
2. Create short clips showing:
   - Offline reward claim
   - Skill effect growing after upgrades
   - Level-up damage numbers increasing
3. Link clips to `/games/idle-hero`.
4. Track:
   - `idle_view`
   - `idle_login_claim`
   - `idle_offline_claim`
   - `idle_upgrade`
   - `idle_enemy_kill`

## Portal Candidates

- CrazyGames
- GameDistribution
- GameMonetize
- itch.io
- Newgrounds

Most portals prefer a standalone HTML5 game package. The Capacitor mobile app is separate from this web deployment.

## Next Build Tasks

- Add custom icon and screenshots.
- Add privacy policy section for games and localStorage.
- Add a simple reset-save button inside the game settings.
- Add balance tuning after observing first-session retention.

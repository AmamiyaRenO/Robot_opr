Project: Voice-Driven Multi-Process Game Launcher (Route A)
Vision

Deliver an end-to-end system on a mini-PC (with Raspberry Pi as sensor bridge) that:

auto-projects to a TV,

runs a voice assistant, and

launches/switches standalone Unity games via an orchestrator.

Key Success Metrics (initial)

Plug in HDMI → reach “Hub/Idle” within ≤10s.

“Open <game>” via voice succeeds on first attempt ≥95% (controlled environment).

Game switch (exit → start → ready) P95 ≤6s.

Crash recovery to Hub ≤5s.

Out of Scope (MVP)

HDMI-CEC control (turn on TV / switch inputs).

Full monitoring dashboards; advanced security hardening.

Multi-language beyond one primary language.

Milestone M0 — MVP End-to-End Flow

Goal: From cold start, user can say “Hey Robot, open <Sample Game>”, see overlay confirmation, game launches, then “back to lobby” returns to Hub.

Entry Criteria: None.

Exit Criteria (DoD):

MQTT broker running locally; basic pub/sub OK.

Orchestrator can launch/quit one sample game via manifest.

Overlay shows toast/confirm; visible over full-screen game.

Voice assistant: wake word → ASR (limited grammar) → intent → orchestrator action.

JSON logs produced for all components; simple rotation configured.

Deliverables (files/scripts):

See M1–M7 [MVP] items below.

Milestone M1 — Baseline & Standards [MVP]

Objective: Establish ports, directories, naming, logging format.

Entry: None.

Exit (DoD):

Baseline doc approved (ports, folders, IDs, topic prefixes, time format).

Logging format = JSON Lines with UTC timestamps.

Deliverables:

docs/baseline.md [MVP]

config/ports.yaml [MVP]

config/logging.json [MVP]

Milestone M2 — Manifest & Topics [MVP]

Objective: Single source of truth for games + stable MQTT API.

Entry: M1 complete.

Exit (DoD):

manifest.json schema validated; includes ≥1 sample game with synonyms.

MQTT topics and payloads fixed: robot/intent, robot/state, robot/overlay, robot/sensor/#, robot/telemetry/#.

Deliverables:

config/manifest.schema.json [MVP]

config/manifest.json [MVP]

docs/topics.md [MVP]

Milestone M3 — MQTT Broker [MVP]

Objective: Local messaging backbone operational.

Entry: M2 ready.

Exit (DoD):

Mosquitto installed/configured (localhost only or basic auth).

Pub/sub smoke test passes.

Deliverables:

tools/mqtt_install_windows.ps1 or tools/mqtt_install_linux.sh [MVP]

config/mosquitto.conf

tools/mqtt_smoke_test.py [MVP]

Milestone M4 — Orchestrator MVP [MVP]

Objective: Start/stop games as isolated processes based on intents.

Entry: M2–M3 ready.

Exit (DoD):

Reads manifest; resolves synonyms → game id.

Launch → healthcheck → running; graceful /quit with timeout → kill fallback.

Handles LAUNCH_GAME, BACK_HOME/QUIT; publishes robot/state.

On crash/exception: return to IDLE and log.

Deliverables:

releases/current/orchestrator/orchestrator.py [MVP]

Modules: manifest.py, process_manager.py, healthcheck.py, intent_router.py

releases/current/orchestrator/requirements.txt [MVP]

tests/test_orchestrator_smoke.py

tools/run_orchestrator.ps1 [MVP]

Milestone M5 — Display & Kiosk [MVP, minimal]

Objective: Ensure uninterrupted full-screen experience.

Entry: M4 functional.

Exit (DoD):

Start in borderless full-screen; foreground focus acquired.

Screensaver/notifications disabled (scripted).

Deliverables:

tools/win_kiosk.ps1 [MVP]

releases/current/orchestrator/focus_win.py [MVP]

(Linux optional) tools/linux_display.sh

Milestone M6 — Overlay (On-Screen Layer) [MVP]

Objective: Visual feedback over any full-screen game.

Entry: M4–M5 ready.

Exit (DoD):

Subscribes robot/overlay; shows toast; supports confirm (YES/NO).

Always on top; transparent; dismissible safeguard.

Deliverables:

releases/current/overlay/overlay_app.(py|exe) [MVP]

releases/current/overlay/requirements.txt [MVP]

tools/run_overlay.ps1 [MVP]

Milestone M7 — Voice Assistant MVP [MVP]

Objective: Wake word → ASR (Vosk) → rules NLU → intent publish → TTS.

Entry: M4–M6 ready.

Exit (DoD):

Mic/VAD + wake word (“Hey Robot”/“你好机器人”).

Vosk streaming with limited grammar (game names, control verbs).

Rules NLU maps to LAUNCH_GAME, BACK_HOME, etc.; low confidence → overlay confirm.

Optional TTS acknowledgment.

Deliverables:

releases/current/voice/voice_assistant.py **[MVP]`

Modules: audio_in.py, wakeword.py, asr_vosk.py, nlu_rules.py, tts.py

releases/current/voice/grammar_*.txt [MVP]

releases/current/voice/requirements.txt [MVP]

tools/run_voice.ps1 [MVP]

config/voice.yaml (optional)

Milestone M8 — Game SDK & Sample Integration [MVP]

Objective: Standard game adapter for health/quit; one sample integrated.

Entry: M4 ready.

Exit (DoD):

Game exposes GET /health → 200; POST /quit → graceful exit.

Sample game launches within 3s; exits cleanly; no resource leaks.

Deliverables:

docs/game_sdk_unity.md [MVP]

releases/current/sdk-unity/GameLocalServer.cs [MVP]

releases/current/sample-game/ (adapted demo)

Milestone M9 — Raspberry Pi Sensor Bridge (Optional for MVP)

Objective: Publish sensor/heartbeat topics from Pi.

Entry: M0–M8 complete.

Exit (DoD):

Periodic publish to robot/sensor/<type>; reconnection & throttling.

Deliverables:

pi/publisher.py, pi/requirements.txt

docs/pi_setup.md

Milestone M10 — Resilience & Watchdog

Objective: Auto-recover critical services; basic safety gating.

Entry: M0 complete.

Exit (DoD):

Orchestrator detects child crashes; auto-return to IDLE and notify overlay.

Voice/overlay auto-restart via simple watchdog.

Whitelist for game paths; basic param sanitization.

Deliverables:

releases/current/orchestrator/watchdog.py

config/whitelist_paths.json

docs/security_basics.md

Milestone M11 — Autostart & Packaging

Objective: One-shot setup; boot-time start.

Entry: M0–M8.

Exit (DoD):

Single script installs deps, registers autostart/services, deploys configs.

Reboot → orchestrator, voice, overlay up automatically (or one-click launcher).

Deliverables:

tools/install_windows.ps1 [MVP]

tools/start_all.ps1 [MVP]

(Linux later) tools/install_linux.sh, systemd/*.service

Milestone M12 — Test & Acceptance [MVP]

Objective: Repeatable E2E tests + demo runbook.

Entry: M0–M8.

Exit (DoD):

E2E script publishes mock intents → verify robot/state; pass ≥10 switch loops.

Live demo script (speech path) validated once end-to-end.

Deliverables:

tests/e2e_smoke.py

tests/e2e_smoke.md [MVP]

docs/demo_runbook.md [MVP]

Milestone M13 — Monitoring, Logs & Ops (Minimal)

Objective: Unified logs; tiny local status page.

Entry: M0.

Exit (DoD):

JSON logs, rotation configured; error levels used consistently.

Local read-only status page: current state, last 20 events, restart buttons.

Deliverables:

releases/current/dashboard/local_status.py

config/logrotate.conf or Python rotation config

docs/ops_playbook.md

Milestone M14 — Documentation & Training

Objective: Make onboarding and deployment simple.

Entry: M0.

Exit (DoD):

Three docs complete: Deploy, Game onboarding, Ops FAQ.

New teammate can deploy and complete “open → exit → open” in ≤1 hour.

Deliverables:

docs/deploy_guide_windows.md

docs/game_onboarding.md

docs/faq.md

Dependencies & Order (for MVP)

M1 → M2 → (M3) → M4 → M5 → M6 → M7 → M8 → M12

M3 (MQTT) can run in parallel with parts of M4/M6.

M5 is minimal (disable interruptions + borderless focus).

M9, M10, M11, M13, M14 are post-MVP enhancers.

Global Definition of Done

Code in repo with runnable scripts and pinned dependencies.

JSON logs with UTC timestamps; no hard-coded absolute paths.

One-command start for each service; one-command stop.

Schema-validated configs; sensible defaults when config missing.

Basic error handling with user-visible overlay feedback.
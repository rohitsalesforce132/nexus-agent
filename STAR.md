# STAR.md — Nexus Agent: Production AI Agent Platform

## Opening Line
> "I built a production-grade AI agent platform called Nexus with 9 subsystems — a markdown-driven soul engine for personality, permission-hardened execution with shell blocklists and folder scoping, a 10-type structured Second Brain memory with conflict resolution and auto-consolidation, token budgets with per-model cost tracking and auto-concise, 3-layer guardrails including bias detection, a complete audit trail, Telegram RBAC with admin/member roles, crash recovery with exponential backoff, and a plugin skill architecture — 52 tests covering every production concern, zero external dependencies."

## Situation
AI agents are exploding, but most are thin wrappers around LLM APIs with no production safeguards. Teams deploying agents face real problems: prompt injection attacks, uncontrolled token spend, no audit trails, no access control, no crash recovery. The mercury-agent project demonstrated a soul-driven approach, but it lacked enterprise concerns — no cost tracking, no bias detection, no structured memory types, no RBAC.

## Task
Build a production AI agent platform that demonstrates every concern a real team would face deploying agents 24/7. The platform needed to be self-contained (zero external dependencies), fully tested, and structured so an interviewer can see exactly how each subsystem works independently and how they integrate in the full agent lifecycle.

## Action
Designed and implemented 9 subsystems as independent Python modules:

1. **Soul Engine** (`src/soul/`) — Agent personality loaded from markdown files (soul.md, persona.md). Configurable tone, humor level, proactivity, and boundaries. Generates the system prompt dynamically — personality is a user-owned document, not hardcoded.

2. **Permission Guard** (`src/permissions/`) — Shell command blocklist with 13 regex patterns (sudo, rm -rf, curl|sh, eval, etc.), folder-level scope rules for read/write/delete, and a human approval flow. Three modes: ASK_ME (safest), ALLOW_ALL (still enforces blocklist).

3. **Second Brain Memory** (`src/memory/`) — 10 structured memory types (identity, preference, goal, project, habit, decision, constraint, relationship, episode, reflection). Each entry has confidence, importance, durability scores. Conflict resolution: higher confidence wins, tie goes to recency. Auto-consolidation prunes stale (>21 days, low durability) and dismissable (>120 days, low confidence) memories.

4. **Token Budget** (`src/budget/`) — Daily token cap with three thresholds: ALLOW (<70%), AUTO_CONCISE (70-100%), BLOCK (>100%). Per-model cost tracking using real pricing for GPT-4o, Claude Sonnet, DeepSeek, Gemini. Budget override for single requests.

5. **3-Layer Guardrails** (`src/guardrails/`) — InputGuard catches prompt injection (4 patterns), PII (SSN, email, phone with auto-redaction), and harmful instructions (SQL injection, system destruction). OutputGuard filters toxic content. BiasDetector flags gender-specific language using word-level matching.

6. **Audit Logger** (`src/audit/`) — Every tool call, permission decision, memory write, guardrail trigger, budget action, channel message, and daemon event logged with timestamp, actor, target, risk level (low/medium/high), and session ID. Queryable by type, risk, and time range.

7. **Channel Router + RBAC** (`src/channels/`) — Multi-channel routing (CLI, Telegram). TelegramRBAC with admin/member roles, access request/approve/reject flow, promote/demote, user listing.

8. **Daemon Manager** (`src/daemon/`) — System service lifecycle (start/stop/restart), crash recovery with exponential backoff (1s→30s max, 10 restarts/minute cap), heartbeat monitoring with configurable intervals.

9. **Skill Registry + Scheduler** (`src/tools/`) — Plugin architecture with install/uninstall/execute. Task scheduler for cron-style recurring skills with tick-based execution.

Wrote 52 tests covering every subsystem independently plus a full end-to-end agent lifecycle test that exercises all 9 subsystems in sequence. Zero external dependencies — pure Python standard library.

## Result
- **52 tests, 0 failures** — every subsystem independently tested plus integration
- **9 production subsystems** — each solving a real deployment concern
- **Zero external dependencies** — runs anywhere Python 3.8+ exists
- **Key differentiators vs similar projects:** Bias detection, per-model cost tracking, 10-type structured memory with conflict resolution, RBAC with role management, complete audit trail, crash recovery with rate limiting

## Follow-Up Questions

**Q: Why 10 memory types instead of just storing everything as text?**
Structured types enable type-specific behavior — identity memories never decay, habits are checked for staleness after 21 days, decisions have high importance scores. You can query "what are this user's goals?" without running a semantic search over raw text.

**Q: How does the conflict resolution work?**
When a new memory overlaps >50% (Jaccard similarity) with an existing memory of the same type, the system compares confidence scores. Higher confidence wins. If equal confidence, the newer memory wins. This prevents the brain from filling with contradictory preferences.

**Q: Why auto-concise at 70% budget?**
At 70% usage, context windows start becoming the bottleneck. Auto-concise triggers context summarization — older conversation turns get compressed into summaries, keeping only recent turns and important memories in full. This extends the effective session length without hitting the hard cap.

**Q: How would you deploy this for 24/7 operation?**
The DaemonManager integrates with systemd or launchd. Crash recovery uses exponential backoff (1s, 2s, 4s, up to 30s max) with a rate limit of 10 restarts per minute. Heartbeat monitoring detects frozen processes — if no heartbeat within 2x the interval, the watchdog triggers a restart.

**Q: Why zero dependencies?**
Interview portability. The code runs in any Python 3.8+ environment without pip install. Every interviewer can clone and run `pytest` immediately. The architecture is the point, not the libraries.

## Key Skills Demonstrated
- Production system design (permissions, budgets, crash recovery)
- Security engineering (input validation, PII redaction, audit trails)
- Cost engineering (per-model token pricing, budget thresholds)
- Agent architecture (soul engine, structured memory, skill plugins)
- Test-driven development (52 tests, 0 failures)

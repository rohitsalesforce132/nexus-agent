# Nexus Agent — Production AI Agent Platform

A soul-driven, permission-hardened AI agent platform with persistent memory, token budgets, multi-channel access, and enterprise-grade safety. Built for 24/7 operation.

## What Makes Nexus Different From Every Other Agent

| Feature | Most Agents | Nexus Agent |
|---------|------------|-------------|
| Permissions | Runs anything | Shell blocklist + folder scoping + approval flow |
| Memory | Ephemeral or basic RAG | 10-type structured memory + auto-extraction + conflict resolution |
| Personality | Hardcoded | Markdown soul files you own and edit |
| Cost Control | None | Daily token budgets with auto-concise |
| Safety | None | 3-layer guardrails (input, output, bias) |
| Audit Trail | None | Every tool call, memory write, and permission decision logged |
| Cost Tracking | None | Per-model, per-team, per-session cost breakdown |
| Multi-Channel | CLI only | CLI + Telegram with admin/member RBAC |
| Uptime | Manual | System service with crash recovery + heartbeat monitoring |
| Extensibility | Custom code | Plugin skills with one-command install |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nexus Agent Platform                      │
│                                                                 │
│  ┌──────────┐  ┌───────────────┐  ┌─────────────────────────┐  │
│  │   Soul    │  │  Permissions  │  │       Guardrails        │  │
│  │  Engine   │  │  Blocklist    │  │  Input Validation       │  │
│  │  (MD)     │  │  Scope Rules  │  │  Output Filter          │  │
│  │           │  │  Approval     │  │  Bias Detection         │  │
│  └─────┬────┘  └──────┬────────┘  └───────────┬─────────────┘  │
│        │               │                       │                │
│        ▼               ▼                       ▼                │
│  ┌──────────┐  ┌───────────────┐  ┌─────────────────────────┐  │
│  │  Memory  │  │    Budget     │  │       Audit Log         │  │
│  │  Second  │  │  Daily Cap    │  │  Tool Calls             │  │
│  │  Brain   │  │  Auto-Concise │  │  Permission Decisions   │  │
│  │  10 Types│  │  Per-Model    │  │  Memory Writes          │  │
│  └─────┬────┘  └──────┬────────┘  └───────────┬─────────────┘  │
│        │               │                       │                │
│        ▼               ▼                       ▼                │
│  ┌──────────┐  ┌───────────────┐  ┌─────────────────────────┐  │
│  │ Channels │  │    Daemon     │  │        Skills           │  │
│  │  CLI     │  │  System Svc   │  │  Install / Schedule     │  │
│  │  Telegram│  │  Crash Recov  │  │  Community Plugins      │  │
│  │  RBAC    │  │  Heartbeat    │  │                         │  │
│  └──────────┘  └───────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Subsystems

| Subsystem | Key Classes | Production Concern |
|-----------|-------------|-------------------|
| **Soul Engine** | `SoulEngine`, `PersonaConfig` | Personality from markdown, not code |
| **Permissions** | `PermissionGuard`, `ScopeRule`, `ApprovalFlow` | Blocklist + folder scoping + human approval |
| **Memory** | `SecondBrain`, `MemoryEntry`, `Consolidator` | 10-type structured memory with SQLite-style storage |
| **Budget** | `TokenBudget`, `CostTracker`, `AutoConcise` | Daily caps, per-model tracking, auto-summarize |
| **Guardrails** | `InputGuard`, `OutputGuard`, `BiasDetector` | 3-layer safety for production |
| **Audit** | `AuditLogger`, `AuditEntry` | Every action logged with timestamp + context |
| **Channels** | `ChannelRouter`, `TelegramRBAC` | Multi-channel with admin/member roles |
| **Daemon** | `DaemonManager`, `CrashRecovery`, `HeartbeatMonitor` | 24/7 uptime with system service |
| **Skills** | `SkillRegistry`, `SkillScheduler` | Plugin architecture with cron scheduling |

## Quick Start

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## STAR.md

See [STAR.md](STAR.md) for interview-ready project summary.

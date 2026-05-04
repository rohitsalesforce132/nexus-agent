# Nexus Agent — End-to-End Architecture

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Request Lifecycle — From User Input to Agent Response](#2-request-lifecycle--from-user-input-to-agent-response)
3. [Subsystem Deep Dives](#3-subsystem-deep-dives)
   - [3.1 Soul Engine](#31-soul-engine)
   - [3.2 Permission Guard](#32-permission-guard)
   - [3.3 Second Brain Memory](#33-second-brain-memory)
   - [3.4 Token Budget](#34-token-budget)
   - [3.5 Guardrails](#35-guardrails)
   - [3.6 Audit Logger](#36-audit-logger)
   - [3.7 Channels & RBAC](#37-channels--rbac)
   - [3.8 Daemon Manager](#38-daemon-manager)
   - [3.9 Skills & Task Scheduler](#39-skills--task-scheduler)
4. [Data Flow Diagrams](#4-data-flow-diagrams)
5. [Production Deployment Topology](#5-production-deployment-topology)
6. [Failure Modes & Recovery](#6-failure-modes--recovery)
7. [Security Model](#7-security-model)
8. [Cost Control Strategy](#8-cost-control-strategy)
9. [Design Decisions & Tradeoffs](#9-design-decisions--tradeoffs)

---

## 1. System Overview

Nexus Agent is a **modular, production-grade AI agent platform** built around 9 independent subsystems. Each subsystem owns a single responsibility and exposes a clean API that other subsystems consume. There are no circular dependencies — data flows in one direction through a well-defined pipeline.

### Architecture Principle: Defense in Depth

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  LAYER 1: GATEWAY                                    │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │ Channels │  │   RBAC    │  │  Input Guardrail  │  │
│  │ (CLI/TG) │──│ Auth/ZK   │──│ Injection + PII   │  │
│  └──────────┘  └───────────┘  └──────────────────┘  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  LAYER 2: COGNITION                                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │  Soul    │  │  Memory   │  │     Budget       │  │
│  │  Engine  │──│ 2nd Brain │──│  Token Tracker   │  │
│  │ (Prompt) │  │ (Context) │  │  (Cost Control)  │  │
│  └──────────┘  └───────────┘  └──────────────────┘  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  LAYER 3: EXECUTION                                  │
│  ┌──────────────┐  ┌───────────┐  ┌─────────────┐  │
│  │ Permissions  │  │   Audit   │  │ Output Guard │  │
│  │ (Blocklist)  │──│  Logger   │──│ Toxic + Bias │  │
│  └──────────────┘  └───────────┘  └─────────────┘  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  LAYER 4: INFRASTRUCTURE                             │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │  Daemon  │  │ Heartbeat │  │     Skills       │  │
│  │ Manager  │──│ Monitor   │──│  Registry + Sched│  │
│  └──────────┘  └───────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Why 4 Layers?

| Layer | Purpose | Failure Impact |
|-------|---------|----------------|
| **Gateway** | Access control, authentication, input sanitization | Blocks unauthorized/malicious inputs before they reach cognition |
| **Cognition** | Personality assembly, context retrieval, cost decisions | Wrong context → wrong answer; overspend → budget exhaustion |
| **Execution** | Action authorization, audit trail, output safety | Unauthorized actions, toxic outputs, untraceable behavior |
| **Infrastructure** | Uptime, health monitoring, extensibility | Agent goes offline, no extensibility |

---

## 2. Request Lifecycle — From User Input to Agent Response

Here's what happens when a user sends "Analyze the network logs for anomalies" through Telegram:

```
Step 1: CHANNEL INGEST
  Telegram message arrives
       │
       ▼
  ChannelRouter.route() → routes to telegram handler
       │
       ▼
  TelegramRBAC.is_authorized(user_id) → checks if user exists in approved list
       │
       ├── NOT AUTHORIZED → TelegramRBAC.request_access() → pending queue
       │                    Agent replies: "Access request sent to admin"
       │
       ▼ (authorized)
       
Step 2: INPUT GUARDRAILS
  InputGuard.check("Analyze the network logs for anomalies")
       │
       ├── PROMPT_INJECTION detected → BLOCKED, AuditLogger logs GUARDRAIL_TRIGGER (risk=high)
       ├── PII detected → auto-redact SSN/email/phone, proceed with sanitized text
       ├── HARMFUL_INSTRUCTION detected → BLOCKED
       │
       ▼ (passed)
  
Step 3: BUDGET CHECK
  TokenBudget.check(estimated_tokens)
       │
       ├── BLOCK → "Daily token budget exhausted"
       ├── AUTO_CONCISE → context is compressed (older turns summarized)
       │
       ▼ (ALLOW)

Step 4: SOUL ASSEMBLY
  SoulEngine.system_prompt → loads soul.md + PersonaConfig
       │
       ▼
  Assembled: "You are Nexus, an AI agent. Tone: direct, helpful...
             Boundaries: Never execute destructive commands..."
  
Step 5: MEMORY RECALL
  SecondBrain.recall("Analyze the network logs for anomalies")
       │
       ├── Searches all 10 memory types for word overlap with query
       ├── Scores by: overlap × importance × confidence × recency_bonus
       ├── Returns top-K entries within max_context_chars (900 chars default)
       │
       ▼
  Injected context: [User prefers Python, Goal: Become AI/ML expert, ...]

Step 6: LLM CALL (simulated in this platform)
  system_prompt + recalled_memories + user_message → LLM
       │
       ▼
  LLM response + token usage
  
Step 7: BUDGET RECORDING
  TokenBudget.record("gpt-4o-mini", input_tokens=3000, output_tokens=2000)
       │
       ▼
  Updates used_tokens, calculates cost using MODEL_PRICES table
  
Step 8: OUTPUT GUARDRAILS
  OutputGuard.check(llm_response)
       │
       ├── TOXIC → blocked, logged
       ├── LOW CONFIDENCE → flagged
       │
       ▼
  BiasDetector.check(llm_response)
       │
       ├── Gender-specific language detected → flagged (not blocked, informational)
       │
       ▼ (passed)

Step 9: EXECUTION (if agent wants to use tools)
  PermissionGuard.check(SHELL_COMMAND, command="grep ERROR /var/log/syslog")
       │
       ├── BLOCKLIST match → BLOCKED (e.g., sudo, rm -rf, curl|sh)
       ├── SCOPE violation → BLOCKED (path not in allowed folders)
       ├── ASK_ME mode → PENDING (waits for human approval)
       │
       ▼ (ALLOWED)

Step 10: AUDIT LOGGING
  AuditLogger.log(TOOL_CALL, "shell_exec", target="/var/log/syslog",
                   result="found 3 errors", risk_level="low")
  
Step 11: RESPONSE DELIVERY
  ChannelRouter routes response back to Telegram
  AuditLogger.log(CHANNEL_MESSAGE, "response_sent")
```

**Every single step is logged. Every decision is traceable.**

---

## 3. Subsystem Deep Dives

### 3.1 Soul Engine

**Location:** `src/soul/__init__.py`
**Classes:** `SoulEngine`, `PersonaConfig`, `SoulFile`

The Soul Engine is the agent's identity layer. Instead of hardcoding personality in Python, it loads markdown files that the **user owns and edits**.

#### File Types

| File | Purpose | Example Content |
|------|---------|-----------------|
| `soul.md` | Core personality, values, boundaries | "Be direct. Don't sugarcoat. Have opinions." |
| `persona.md` | Behavioral parameters | Humor level, proactivity, language |
| `taste.md` | Preferences and opinions | "Prefers Go over Python for systems work" |
| `heartbeat.md` | Periodic task checklist | "Check email, calendar, weather" |

#### PersonaConfig Parameters

```python
@dataclass
class PersonaConfig:
    name: str = "Nexus"              # Agent name
    tone: str = "direct, helpful"    # Communication style
    language: str = "en"             # Language code
    humor_level: float = 0.3         # 0.0 (none) → 1.0 (constant)
    proactivity: float = 0.7         # 0.0 (reactive) → 1.0 (very proactive)
    boundaries: list[str]            # Hard rules the agent never violates
    custom_instructions: str         # User-defined additions
```

#### How System Prompt is Assembled

```
1. Base personality from PersonaConfig → "You are Nexus. Tone: direct..."
2. Humor/proactivity thresholds → "Humor: 30%. Be witty when it lands."
3. Boundaries → list format, one per line
4. Soul file content → appended as "# Soul" section
5. Final prompt = base + humor + boundaries + soul_content
```

**Design choice:** Soul files are markdown because users can edit them in any text editor, version them in git, and read them without understanding code. The agent's personality is a **document**, not a deployment.

---

### 3.2 Permission Guard

**Location:** `src/permissions/__init__.py`
**Classes:** `PermissionGuard`, `ScopeRule`, `PermissionResult`

The Permission Guard is a 3-tier authorization system that prevents the agent from executing dangerous actions, even if the LLM tries to.

#### Tier 1: Shell Command Blocklist

13 regex patterns that **always block**, regardless of permission mode:

| Pattern | Blocks | Why |
|---------|--------|-----|
| `\bsudo\b` | `sudo anything` | Privilege escalation |
| `\brm\s+-rf\s+/` | `rm -rf /` | Recursive root deletion |
| `\bmkfs\b` | `mkfs /dev/sda` | Disk formatting |
| `\bdd\s+if=` | `dd if=/dev/zero` | Raw disk writes |
| `>\s*/dev/sd` | `data > /dev/sda` | Direct disk writes |
| `\bchmod\s+777` | `chmod 777` | World-writable permissions |
| `\bchown\s+root` | `chown root` | Ownership to root |
| `\bsystemctl\s+(stop\|disable)\s+(ssh\|firewall)` | Disabling SSH/firewall | Lockout prevention |
| `\biptables\s+-F` | `iptables -F` | Flush firewall rules |
| `\bcurl\s+.*\|\s*sh` | `curl \| sh` | Remote code execution |
| `\bwget\s+.*\|\s*sh` | `wget \| sh` | Remote code execution |
| `\beval\b` | `eval $INPUT` | Arbitrary code execution |
| `\bexec\b` | `exec $CMD` | Arbitrary code execution |

#### Tier 2: Folder Scope Rules

```python
ScopeRule(
    path="/home/user/workspace",    # Protected directory
    allow_read=True,                # Can read files
    allow_write=True,               # Can create/edit files
    allow_delete=False,             # Cannot delete files
)
```

Scope rules are additive — if any rule allows the action on the target path, it passes. If no rules cover the path, the action is **blocked by default**.

#### Tier 3: Human Approval Flow

In `ASK_ME` mode, dangerous actions (file delete, message send, shell commands) are queued as `PENDING`:

```
Agent wants to run: python3 deploy.py
    │
    ▼
PermissionGuard.check() → PENDING
    │
    ▼
Notification to admin: "Nexus wants to run: python3 deploy.py"
    │
    ├── Admin says "yes" → approve() → ALLOWED
    └── Admin says "no"  → deny()   → BLOCKED
```

#### Permission Modes

| Mode | Blocklist | Scope | Approval | Use Case |
|------|-----------|-------|----------|----------|
| `ASK_ME` | ✅ Always | ✅ Always | ✅ For dangerous actions | Production (default) |
| `ALLOW_ALL` | ✅ Always | ✅ Always | ❌ Skipped | Development |

**Even in ALLOW_ALL mode, the blocklist and scope rules are enforced.** The approval flow is the only thing that's relaxed.

---

### 3.3 Second Brain Memory

**Location:** `src/memory/__init__.py`
**Classes:** `SecondBrain`, `MemoryEntry`, `MemoryType`

The Second Brain is a **structured persistent memory** with 10 types, confidence scoring, and automatic lifecycle management.

#### The 10 Memory Types

| Type | Purpose | Durability | Example |
|------|---------|------------|---------|
| `IDENTITY` | Who the user is | High (0.9) | "Name: Rohit, DevOps engineer at tier-1 carrier" |
| `PREFERENCE` | What they like | Medium (0.6) | "Prefers dark mode, hates JavaScript" |
| `GOAL` | What they're working toward | High (0.8) | "Transition to AI/ML engineering" |
| `PROJECT` | Active projects | Medium (0.7) | "Building interview prep portfolio" |
| `HABIT` | Behavioral patterns | Low (0.4) | "Works late, prefers morning meetings" |
| `DECISION` | Past decisions | High (0.8) | "Chose Python over Go for the API" |
| `CONSTRAINT` | Things to avoid | High (0.9) | "No sudo access, no Docker" |
| `RELATIONSHIP` | People in their life | Medium (0.6) | "Manager: Suresh, skip-level: Priya" |
| `EPISODE` | Notable events | Low (0.3) | "Deployed to prod on Friday, caused outage" |
| `REFLECTION` | Agent-generated insights | Medium (0.5) | "User responds better to direct feedback" |

#### Memory Entry Structure

```python
@dataclass
class MemoryEntry:
    memory_type: MemoryType      # One of 10 types
    content: str                 # The actual memory text
    confidence: float = 0.8      # 0-1: How confident is this memory?
    importance: float = 0.5      # 0-1: How important for context?
    durability: float = 0.5      # 0-1: How long until decay?
    source: str = "conversation" # Where did this come from?
    created_at: float            # Unix timestamp
    last_accessed: float         # Updated on every recall
    access_count: int = 0        # How often this memory is used
    metadata: dict               # Arbitrary key-value pairs
    entry_id: str                # SHA256 hash (auto-generated)
```

#### Recall Scoring Formula

When recalling memories for context injection, each candidate is scored:

```
score = word_overlap × importance × confidence × recency_bonus

where:
  word_overlap = |query_words ∩ memory_words|
  recency_bonus = max(0.5, 1.0 - (now - last_accessed) / 86400)
```

Memories are ranked by score, then truncated to fit within `max_context_chars` (default 900 chars). This ensures the LLM context window isn't flooded with memory — only the most relevant, important, recent memories make the cut.

#### Conflict Resolution

When a new memory overlaps >50% (Jaccard similarity) with an existing memory of the same type:

```
if new.confidence > existing.confidence:
    → REPLACE existing with new
elif new.confidence == existing.confidence:
    → NEWER one wins (higher created_at)
else:
    → KEEP existing, discard new
```

This prevents the brain from filling with contradictory memories ("Likes Python" vs "Prefers Go") — the higher-confidence memory always wins.

#### Auto-Consolidation Lifecycle

```
Every consolidation cycle:
  1. Scan all memories
  2. Prune STALE memories:
     - durability < 0.3 AND age > 21 days → DELETE
  3. Prune DISMISSABLE memories:
     - confidence < 0.5 AND durability >= 0.3 AND age > 120 days → DELETE
  4. Return report: {total, by_type, pruned_count}
```

**Design choice:** Stale memories (low durability, old) are aggressively pruned at 21 days. Dismissable memories (low confidence but normal durability) get a longer grace period of 120 days — they might be confirmed later.

---

### 3.4 Token Budget

**Location:** `src/budget/__init__.py`
**Classes:** `TokenBudget`, `UsageRecord`, `ModelPricing`

The Token Budget system controls LLM spend with per-model cost tracking using **real pricing data**.

#### Budget Thresholds

```
Daily Token Usage
│
├── 0% ──────────── ALLOW (normal operation)
│
├── 70% ─────────── AUTO_CONCISE (compress context to save tokens)
│                   → Older conversation turns summarized
│                   → Memory recall returns fewer entries
│                   → System prompt trimmed
│
├── 100% ────────── BLOCK (no more LLM calls today)
│                   → Agent responds: "Daily token budget exhausted"
│                   → Override possible for emergencies
│
└── Override ─────── ALLOW once (admin-triggered budget override)
                    → Resets after single request
```

#### Per-Model Pricing Table

| Model | Input/1M tokens | Output/1M tokens | Provider |
|-------|----------------|------------------|----------|
| `gpt-4o-mini` | $0.15 | $0.60 | OpenAI |
| `gpt-4o` | $2.50 | $10.00 | OpenAI |
| `claude-sonnet` | $3.00 | $15.00 | Anthropic |
| `claude-haiku` | $0.25 | $1.25 | Anthropic |
| `deepseek-chat` | $0.14 | $0.28 | DeepSeek |
| `gemini-pro` | $1.25 | $5.00 | Google |

#### Cost Calculation

```python
cost = (input_tokens / 1_000_000 × input_price) + (output_tokens / 1_000_000 × output_price)
```

Example: 5,000 input + 2,000 output tokens on `gpt-4o`:
```
(5000/1000000 × $2.50) + (2000/1000000 × $10.00) = $0.0125 + $0.02 = $0.0325
```

#### Auto-Concise Mechanism

When `usage_pct >= 70%`:

1. **System prompt:** Trim custom instructions, keep only boundaries
2. **Memory recall:** Reduce `max_context_chars` from 900 → 300
3. **Conversation history:** Compress turns older than 5 messages into a single summary line
4. **Net effect:** Reduces token consumption by ~40-60%, extending session life

---

### 3.5 Guardrails

**Location:** `src/guardrails/__init__.py`
**Classes:** `InputGuard`, `OutputGuard`, `BiasDetector`

Three independent safety layers, each with a distinct responsibility.

#### Layer 1: InputGuard

| Check | Patterns | Action |
|-------|----------|--------|
| **Prompt Injection** | `"ignore previous instructions"`, `"you are now DAN"`, `"forget your rules"`, `"system: you"` | BLOCK |
| **PII Detection** | SSN (`\d{3}-\d{2}-\d{4}`), Email, Phone | AUTO-REDACT → replace with `[SSN-REDACTED]` |
| **Harmful Instructions** | `DROP TABLE`, `sudo rm`, `how to hack` | BLOCK |

PII is **not blocked** — it's **redacted**. The agent can still process the request, but the PII is replaced with placeholder tokens before it reaches the LLM.

#### Layer 2: OutputGuard

| Check | Detection Method | Action |
|-------|-----------------|--------|
| **Toxicity** | Keyword matching against {hate, violent, kill, attack, harm, threat} | BLOCK |
| **Low Confidence** | Confidence score < 0.5 | FLAG (not blocked) |

#### Layer 3: BiasDetector

Uses **word-level matching** (not substring) to detect gendered language:

```python
# Tokenize input into words
words = set(re.split(r'\W+', text.lower())) - {''}

# Check against proxy terms
if words & {"he", "him", "his", "man", "husband", "father"}:
    → flag as gender-specific (informational, not blocking)
```

**Why word-level?** Substring matching (`"he" in "the"`) produces false positives. Word boundaries (`\b`) ensure only actual pronouns are flagged.

**Why not blocking?** Bias detection is informational — it flags the output for review but doesn't block it. In production, this feeds into the audit log and can trigger human review workflows.

---

### 3.6 Audit Logger

**Location:** `src/audit/__init__.py`
**Classes:** `AuditLogger`, `AuditEntry`

Every action the agent takes is logged with full context.

#### Event Types

| Event Type | When Logged | Risk Levels |
|------------|-------------|-------------|
| `TOOL_CALL` | Every tool execution | low (read), medium (write), high (shell) |
| `PERMISSION_DECISION` | Every allow/block/pending | low (allowed), high (blocked) |
| `MEMORY_WRITE` | Every new memory stored | low |
| `MEMORY_READ` | Every memory recall | low |
| `GUARDRAIL_TRIGGER` | Every guardrail block/flag | medium (PII), high (injection) |
| `BUDGET_ACTION` | Budget threshold changes | medium (auto-concise), high (block) |
| `CHANNEL_MESSAGE` | Every message sent/received | low |
| `DAEMON_EVENT` | Start/stop/crash/recovery | medium (restart), high (crash) |

#### Audit Entry Structure

```python
@dataclass
class AuditEntry:
    event_type: AuditEventType    # What happened
    action: str                    # Specific action (e.g., "read_file")
    actor: str = "nexus"          # Who initiated (agent or user)
    target: str = ""              # What was affected (file path, command)
    result: str = ""              # Outcome
    details: dict                 # Arbitrary metadata
    timestamp: float              # Unix timestamp
    session_id: str               # Session for grouping
    risk_level: str               # "low" | "medium" | "high"
```

#### Query Capabilities

```python
# All high-risk events
audit.query(risk_level="high")

# All permission decisions since timestamp
audit.query(event_type=PERMISSION_DECISION, since=1714000000)

# Last 50 tool calls
audit.query(event_type=TOOL_CALL, limit=50)

# Event count summary
audit.event_counts  → {"tool_call": 45, "permission_decision": 12, ...}
```

#### Ring Buffer

The audit log caps at 10,000 entries. When exceeded, the oldest entries are dropped. This prevents unbounded memory growth in long-running sessions.

---

### 3.7 Channels & RBAC

**Location:** `src/channels/__init__.py`
**Classes:** `ChannelRouter`, `TelegramRBAC`, `ChannelUser`

#### Supported Channels

| Channel | Protocol | Use Case |
|---------|----------|----------|
| `CLI` | Standard I/O | Local development, scripting |
| `Telegram` | Bot API | Mobile access, notifications, 24/7 availability |

#### Telegram RBAC Flow

```
User sends /start to Telegram bot
    │
    ▼
TelegramRBAC.request_access(user_id, username)
    │
    ├── Already approved → return role (admin/member)
    │
    └── New user → add to pending queue
                   notify admin: "New access request from @username"
    │
    ▼
Admin reviews
    │
    ├── Admin approves → approve(user_id, as_admin=False) → member role
    ├── Admin approves as admin → approve(user_id, as_admin=True) → admin role
    └── Admin rejects → reject(user_id) → removed from pending
```

#### Admin Capabilities

| Action | Method | Effect |
|--------|--------|--------|
| Approve access | `approve(user_id)` | User becomes member |
| Approve as admin | `approve(user_id, as_admin=True)` | User becomes admin |
| Reject access | `reject(user_id)` | User stays blocked |
| Promote to admin | `promote(user_id)` | member → admin |
| Demote to member | `demote(user_id)` | admin → member |
| Remove user | `remove(user_id)` | Revokes all access |

---

### 3.8 Daemon Manager

**Location:** `src/daemon/__init__.py`
**Classes:** `DaemonManager`, `CrashRecovery`, `HeartbeatMonitor`

#### Lifecycle States

```
STOPPED ──start()──→ STARTING ──→ RUNNING
    ▲                                  │
    │                          crash / stop()
    │                                  │
    │              ┌───────────────────┤
    │              ▼                   ▼
    │         RECOVERING            CRASHED
    │              │                   │
    │              ▼                   │
    │         auto-recovered           │
    │              │                   │
    └──stop()──────┘                   │
         (manual intervention)         │
                                      ▼
                                  (needs manual restart)
```

#### Crash Recovery — Exponential Backoff

```
Crash 1: wait 1s  → restart
Crash 2: wait 2s  → restart
Crash 3: wait 4s  → restart
Crash 4: wait 8s  → restart
Crash 5: wait 16s → restart
Crash 6: wait 30s → restart (capped at 30s)
Crash 7: wait 30s → restart
...
Crash 11 (< 60s): RECOVERY FAILED — rate limit hit (10/min)
```

**Rate limit:** Max 10 restarts per rolling 60-second window. If exceeded, the daemon enters `CRASHED` state and requires manual intervention. This prevents crash loops from consuming resources.

#### Heartbeat Monitoring

```
Every 30 seconds (configurable):
    HeartbeatMonitor.beat() → records timestamp

Health check:
    if (now - last_heartbeat) < interval × 2:
        → healthy
    else:
        → unhealthy (agent may be frozen)
        → trigger watchdog restart
```

The 2x multiplier gives the agent a grace period — a single missed heartbeat doesn't trigger recovery.

---

### 3.9 Skills & Task Scheduler

**Location:** `src/tools/__init__.py`
**Classes:** `SkillRegistry`, `Skill`, `TaskScheduler`, `ScheduledTask`

#### Skill Lifecycle

```
1. INSTALL
   SkillRegistry.install(Skill(
       name="log-analyzer",
       version="1.0.0",
       description="Analyze system logs for anomalies",
       handler=analyze_logs_function,
   ))

2. EXECUTE
   SkillRegistry.execute("log-analyzer", params={"path": "/var/log/syslog"})
   → handler is called with params dict
   → returns result

3. UNINSTALL
   SkillRegistry.uninstall("log-analyzer")
   → removed from registry
```

#### Task Scheduling

```python
# Schedule a recurring task
TaskScheduler.schedule(
    task_id="morning-report",
    skill_name="log-analyzer",
    schedule="0 9 * * *",  # Cron expression
)

# Tick-based execution (called by daemon heartbeat)
due_tasks = TaskScheduler.tick()
for task in due_tasks:
    SkillRegistry.execute(task.skill_name)
```

Tasks are checked on every daemon heartbeat tick. A task is "due" if it hasn't run in the last 60 seconds (simplified — a production version would parse the cron expression).

---

## 4. Data Flow Diagrams

### 4.1 Inbound Message Flow

```
┌──────────┐     ┌─────────────┐     ┌────────────┐     ┌──────────────┐
│  User    │────▶│  Channel    │────▶│  Input     │────▶│  Budget      │
│  (TG/CLI)│     │  Router     │     │  Guardrail │     │  Check       │
└──────────┘     └──────┬──────┘     └─────┬──────┘     └──────┬───────┘
                        │                   │                    │
                   RBAC check         Sanitize PII         ALLOW/CONCISE/
                   Authorized?        Block injection?       BLOCK
                        │                   │                    │
                        ▼                   ▼                    ▼
                 ┌──────────────────────────────────────────────────────┐
                 │              IF ALLOWED: Continue                    │
                 └──────────────────────┬───────────────────────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │   Soul Engine     │──▶ System Prompt
                              │   Memory Recall   │──▶ Context
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │   LLM Call       │
                              │   (simulated)    │
                              └────────┬─────────┘
                                       │
                                       ▼
                 ┌──────────────────────────────────────────────────────┐
                 │              Output Pipeline                         │
                 │  OutputGuard ──▶ BiasDetector ──▶ Audit Log         │
                 └──────────────────────┬───────────────────────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │   Permission     │
                              │   Guard          │
                              │  (if tool use)   │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │   Channel        │────▶ User
                              │   Router         │
                              └──────────────────┘
```

### 4.2 Memory Write Flow

```
User says something memorable
    │
    ▼
MemoryEntry created with:
  - type (auto-detected or explicit)
  - content
  - confidence (0-1)
  - importance (0-1)
  - durability (0-1)
    │
    ▼
SecondBrain.store(entry)
    │
    ├── Find conflicts (same type, >50% word overlap)
    │       │
    │       ├── Conflict found → resolve:
    │       │     higher confidence wins → replace existing
    │       │     tie → newer wins
    │       │     lower → keep existing, discard new
    │       │
    │       └── No conflict → store directly
    │
    ▼
AuditLogger.log(MEMORY_WRITE, ...)
```

---

## 5. Production Deployment Topology

```
┌──────────────────────────────────────────────────────┐
│  Host Machine (Linux/macOS)                          │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  systemd / launchd service                     │  │
│  │  ┌──────────────────────────────────────────┐  │  │
│  │  │  Nexus Agent Daemon (PID: 12345)         │  │  │
│  │  │                                          │  │  │
│  │  │  ┌─────────┐  ┌───────────┐  ┌────────┐ │  │  │
│  │  │  │ Soul    │  │ Memory    │  │ Guard  │ │  │  │
│  │  │  │ Engine  │  │ (SQLite)  │  │ Rails  │ │  │  │
│  │  │  └─────────┘  └───────────┘  └────────┘ │  │  │
│  │  │  ┌─────────┐  ┌───────────┐  ┌────────┐ │  │  │
│  │  │  │ Budget  │  │ Audit     │  │ Skills │ │  │  │
│  │  │  │ Tracker │  │ Logger    │  │ Reg.   │ │  │  │
│  │  │  └─────────┘  └───────────┘  └────────┘ │  │  │
│  │  │  ┌─────────┐  ┌───────────┐  ┌────────┐ │  │  │
│  │  │  │ Channel │  │ Permis-   │  │ Daemon │ │  │  │
│  │  │  │ Router  │  │ sions     │  │ Mgr    │ │  │  │
│  │  │  └─────────┘  └───────────┘  └────────┘ │  │  │
│  │  └──────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ soul.md  │  │ persona  │  │ ~/.nexus/        │   │
│  │ taste.md │  │ .md      │  │  ├── memory.db   │   │
│  │ heartb.  │  │          │  │  ├── audit.log   │   │
│  └──────────┘  └──────────┘  │  └── skills/     │   │
│                               └──────────────────┘   │
└──────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
    ┌─────────┐              ┌──────────────┐
    │ Telegram │              │ LLM Provider │
    │ Bot API  │              │ (OpenAI/     │
    └─────────┘              │  Anthropic/   │
                             │  DeepSeek)    │
                             └──────────────┘
```

---

## 6. Failure Modes & Recovery

| Failure | Detection | Recovery | Data Impact |
|---------|-----------|----------|-------------|
| **LLM timeout** | Budget check fails | Retry with cheaper model | None |
| **OOM crash** | Daemon heartbeat missed | Exponential backoff restart | In-flight request lost |
| **Crash loop** | >10 crashes/minute | Enter CRASHED state, alert admin | None |
| **Budget exhaustion** | usage_pct ≥ 100% | Block LLM calls until reset | None |
| **Prompt injection** | InputGuard pattern match | Block + audit log (risk=high) | None |
| **PII leak** | InputGuard PII patterns | Auto-redact before LLM | Sanitized copy only |
| **Toxic output** | OutputGuard keywords | Block response | None |
| **Unauthorized access** | RBAC check fails | Reject, notify admin | None |
| **Permission violation** | Blocklist + scope check | Block + audit log | None |
| **Memory corruption** | Conflict resolution | Higher confidence wins | Weaker memory discarded |

---

## 7. Security Model

```
                    TRUST BOUNDARY
                    │
   EXTERNAL         │    INTERNAL
                    │
   User ────────────┼──── ChannelRouter ──── TelegramRBAC
   (untrusted)      │         │
                    │         ▼
                    │    InputGuard ──────── PII Redaction
                    │         │               Injection Block
                    │         ▼
                    │    TokenBudget ──────── Cost Control
                    │         │
                    │         ▼
                    │    SoulEngine ───────── System Prompt
                    │    SecondBrain ──────── Memory Recall
                    │         │
                    │         ▼
                    │    LLM Provider ─────── External API
                    │         │
                    │         ▼
                    │    OutputGuard ──────── Toxicity Block
                    │    BiasDetector ─────── Bias Flagging
                    │         │
                    │         ▼
                    │    PermissionGuard ──── Blocklist
                    │         │               Scope Rules
                    │         ▼               Approval Flow
                    │    AuditLogger ──────── Full Trail
                    │
   LLM Provider ────┼──── (external API call)
   (semi-trusted)   │
                    │
```

### Security Principles

1. **Never trust input** — InputGuard runs before any processing
2. **Never trust output** — OutputGuard + BiasDetector run before delivery
3. **Default deny** — PermissionGuard blocks anything not explicitly allowed
4. **Audit everything** — AuditLogger captures every decision
5. **Minimize blast radius** — Scope rules limit file access to approved directories
6. **Human in the loop** — ASK_ME mode requires approval for dangerous actions

---

## 8. Cost Control Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Cost Control Hierarchy                    │
│                                                             │
│  Level 1: MODEL SELECTION                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Choose cheapest model that meets quality bar:       │    │
│  │  - Simple Q&A → gpt-4o-mini ($0.15/$0.60 per 1M)   │    │
│  │  - Complex reasoning → claude-sonnet ($3.00/$15.00) │    │
│  │  - Code generation → deepseek-chat ($0.14/$0.28)    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Level 2: CONTEXT COMPRESSION                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  At 70% budget: AUTO_CONCISE                        │    │
│  │  - Trim system prompt                               │    │
│  │  - Reduce memory context from 900 → 300 chars       │    │
│  │  - Summarize old conversation turns                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Level 3: HARD CAP                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  At 100% budget: BLOCK all LLM calls                │    │
│  │  - Admin can override for emergencies               │    │
│  │  - Budget resets daily (rolling 24h window)         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Level 4: VISIBILITY                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  TokenBudget.status:                                │    │
│  │  {                                                  │    │
│  │    "daily_limit": 500000,                           │    │
│  │    "used": 350000,                                  │    │
│  │    "usage_pct": 70.0,                               │    │
│  │    "total_cost": 0.0234,                            │    │
│  │    "cost_by_model": {                               │    │
│  │      "gpt-4o-mini": 0.0012,                        │    │
│  │      "claude-sonnet": 0.0182                        │    │
│  │    }                                                │    │
│  │  }                                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Design Decisions & Tradeoffs

### Decision 1: Zero External Dependencies

**Choice:** Pure Python standard library, no pip install required.
**Tradeoff:** No SQLite, no async, no real LLM client.
**Why:** Interview portability. Every interviewer can clone and run `pytest` immediately. The architecture is the deliverable.

### Decision 2: Word-Overlap Retrieval Over Vector Similarity

**Choice:** Memory recall uses word overlap (Jaccard-like) scoring.
**Tradeoff:** Less semantically accurate than embedding-based retrieval.
**Why:** No numpy/FAISS dependency needed. For a portfolio project, the scoring formula (`overlap × importance × confidence × recency`) demonstrates the concept without requiring a vector database.

### Decision 3: Keyword-Based Guardrails Over ML Classifiers

**Choice:** InputGuard and OutputGuard use regex and keyword matching.
**Tradeoff:** Higher false positive/negative rates than ML-based content moderation.
**Why:** Deterministic, testable, no model serving infrastructure. In production, you'd plug in Perspective API or AWS Comprehend — but the architecture (3-layer pipeline with PII redaction) is the same.

### Decision 4: Ring Buffer Audit Log Over Append-Only File

**Choice:** In-memory list capped at 10,000 entries.
**Tradeoff:** Old entries are lost; not durable across restarts.
**Why:** Keeps the codebase simple. In production, this would be a write-ahead log file or external service (Datadog, Splunk).

### Decision 5: Structured Memory Types Over Flat Key-Value

**Choice:** 10 explicit memory types with type-specific behavior.
**Tradeoff:** More complex storage; requires type classification on store.
**Why:** Type-specific decay rates, confidence thresholds, and conflict resolution. "Identity" memories should never be pruned; "habits" should be re-validated after 21 days. Flat key-value can't do this.

### Decision 6: Exponential Backoff Crash Recovery

**Choice:** 1s → 2s → 4s → 8s → 16s → 30s (capped), max 10/min.
**Tradeoff:** Slower recovery for frequent crashes.
**Why:** Crash loops are worse than slow recovery. The rate limit prevents the agent from consuming resources in an infinite restart loop.

---

*This architecture document covers every subsystem, data flow, failure mode, and design decision in the Nexus Agent platform. For test coverage details, see `tests/test_all.py`. For interview preparation, see `STAR.md`.*

---
inclusion: always
---

# Opensquad — Project Instructions

This project uses **Opensquad**, a multi-agent orchestration framework.

## Quick Start

Type `/opensquad` to open the main menu, or use any of these commands:
- `/opensquad create` — Create a new squad
- `/opensquad run <name>` — Run a squad
- `/opensquad help` — See all commands

## Directory Structure

- `_opensquad/` — Opensquad core files (do not modify manually)
- `_opensquad/_memory/` — Persistent memory (company context, preferences)
- `skills/` — Installed skills (integrations, scripts, prompts)
- `squads/` — User-created squads
- `squads/{name}/_investigations/` — Sherlock content investigations (profile analyses)
- `squads/{name}/output/` — Generated content and files
- `_opensquad/_browser_profile/` — Persistent browser sessions (login cookies, localStorage)

The `/opensquad` command is provided by the Kiro skill at `.kiro/skills/opensquad/SKILL.md`. Type `/opensquad` in chat (it appears in the `/` menu with the 🌐 skill icon) to start.

## How It Works

1. The `/opensquad` skill is the entry point for all interactions
2. The **Architect** agent creates and modifies squads
3. During squad creation, the **Sherlock** investigator can analyze reference profiles (Instagram, YouTube, Twitter/X, LinkedIn) to extract real content patterns
4. The **Pipeline Runner** executes squads automatically
5. Agents communicate via persona switching (inline) or subagents (background)
6. Checkpoints pause execution for user input/approval

## Rules

- Always use `/opensquad` commands to interact with the system
- Do not manually edit files in `_opensquad/core/` unless you know what you're doing
- Squad YAML files can be edited manually if needed, but prefer using `/opensquad edit`
- Company context in `_opensquad/_memory/company.md` is loaded for every squad run

## Kiro Environment: Subagents

In Kiro, background subagents (via `invoke_sub_agent`) are only available in Autopilot mode. When agent instructions (e.g., from the Architect) say to "use the Task tool with run_in_background: true" or similar and background subagents are not available, you MUST instead execute all tasks inline and sequentially:

1. Inform the user you will process the tasks one by one
2. Execute each task in the current conversation — do NOT skip or defer any of them
3. Complete ALL tasks before asking the next question or moving on

Never announce that you "will do something in parallel" and then skip the work. Always do the actual research inline before continuing.

## Checkpoint Handling (Kiro)

Checkpoint steps always execute inline (they require direct user input and are never dispatched as subagents).

- ALWAYS present checkpoints to the user — never skip them
- When presenting options, use a numbered list (1. / 2. / 3.) and tell the user to reply with the option number
- Ask one question at a time and wait for the answer before proceeding

## Browser Sessions

Opensquad uses a persistent Playwright browser profile to keep you logged into social media platforms.
- Sessions are stored in `_opensquad/_browser_profile/` (gitignored, private to you)
- First time accessing a platform, you'll log in manually once
- Subsequent runs will reuse your saved session
- **Important:** Opensquad uses its own `@playwright/mcp` server configured in `.kiro/settings/mcp.json`.

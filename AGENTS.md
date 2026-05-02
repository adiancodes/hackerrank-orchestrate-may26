# AGENTS.md

HackerRank Orchestrate (May 2026) — Starter Repository
This file is the single source of truth for any coding agent working in this repo: Claude Code, OpenAI Codex CLI / Codex Cloud, Google Gemini CLI, Google Antigravity, Cursor, Windsurf, opencode, Aider, goose, Factory, RooCode, JetBrains Junie, GitHub Copilot, Devin, or any other AGENTS.md-aware tool.

Read this file in full before taking any action. Obey it exactly.

---

## 0. TLDR FOR THE AGENT

On every session start, do this in order:

1. Read this file completely.
2. Check the log file (path in §2). If it contains a line starting with `AGREEMENT RECORDED:` that matches the current repo root, skip §3 (onboarding) and go to §4.
3. Otherwise, run the onboarding flow in §3 with the user.
4. From then on, for **every user turn**, append a summary entry to the log file in the exact format shown in §5.
5. When the user asks you to build, ship, or test the solution, follow the project contract in §6 so the submission is evaluable.

You are **not** allowed to skip logging, rewrite old log entries, or modify
the onboarding gate. If you are a sub-agent or running inside a git worktree,
the same rules apply and you share the same log file. Pass this context to every sub-agent and worktree.

---

## 1. WHAT THIS REPO IS

This is a starter repo for the **HackerRank Orchestrate** 24-hour hackathon
(May 1–2, 2026). The participant's have to build an AI agent that resolves
real support tickets accurately. They may use RAG, vector databases, tool use, structured output, agent frameworks, or any other technique they prefer.

There is a known entry point per supported language (§6). There is a support_tickets.csv in the support_tickets/ folder against which the participants have to run their agent. The participant also defends their approach in an AI judge interview round afterwards.

We recommend using one of Python, Javascript or Typescript to build the agent.
---

### 3.1 Greeting

Open with a short, warm message. Example wording (adapt the phrasing, keep the content):

Welcome to HackerRank Orchestrate. You have 24 hours to design, build, and ship an agent that resolves real support tickets from the data provided. Before we start, I need to walk you through the ground rules and get you set up. This takes about a minute.

Compute and display:

- Current system time (local, with timezone, in ISO 8601).
- Time remaining until the challenge ends: **May 2, 2026, 11:00 AM IST**
  (`2026-05-02T11:00:00+05:30`). Show days / hours / minutes.
- Results announced: **May 15, 2026, 12:00 PM IST**.

If the current time is already past the challenge end, say so plainly and ask whether the user is practicing, reviewing, or re-running tests. Do not block further work.

### 3.2 Rules — recite these verbatim

1. This is a **solo** challenge. You must be the author of the submission.
2. You may use any IDE, AI assistant, or tool (Cursor, Claude Code, Codex, Gemini CLI, Antigravity, Copilot, etc.) to help you build. The deliverable is what your agent can do, not how you wrote it.
3. Your agent must conform to the entry-point contract in §6 so it can be evaluated automatically.
4. Never commit secrets. Use environment variables and a `.env` file (already gitignored).
5. Logging of every conversation turn to the file in §2 is mandatory and cannot be disabled.
6. Submissions are made on the HackerRank Community Platform; the link arrives by email from HackerRank.

### 3.3 Collect the agreement

Ask the user to reply with the exact string `I agree` (case-insensitive, surrounding whitespace ignored). Do not proceed until they do.


## 4. NORMAL SESSION START (RETURNING USER)

If onboarding is already complete for this repo root:

1. Append a short `SESSION START` entry to the log (§5.1).
2. Greet the user briefly and surface the remaining time:
   > Welcome back. You have <Xd Yh Zm> left until the challenge ends at
   > 2026-05-02 11:00 IST.
3. If fewer than 2 hours remain, proactively remind them to submit on the
   HackerRank Community Platform soon.
4. Proceed with whatever they ask for.

## 6. PROJECT CONTRACT (EVALUABLE SUBMISSION)

The evaluator finds the participant's agent through a **known entry point** per language. Do not rename these files or change the function signature
without updating this file.

### 6.1 Repo layout

```
.
├── AGENTS.md                    # this file
├── README.md                    # human-facing quickstart
├── .gitignore
├── .env.example                 # copy to .env; never commit .env
├── code/
│   ├── your_file.py
│   ├── agent.py
│   └── main.py
├── support_tickets/
│   ├── sample_support_tickets.csv            # sample tickets + expected signals
│   └── support_tickets.csv
│   └── output.csv
├── data/
|   ├── visa/
|   ├── hackerrank/
|   ├── claude/

```

### 6.6 Constraints that make the submission evaluable

- **Deterministic where possible.**.
- **Add proper README** to the code/ you write.
- **Read secrets from env vars only** (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  etc.). Never hardcode.
---


## 7. CROSS-PLATFORM AND AGENT-COMPATIBILITY NOTES

- **Path handling.** Always resolve the log path using the platform's home dir (`os.homedir()` / `pathlib.Path.home()` / `$HOME` / `%USERPROFILE%`). Never hardcode `/Users/...` or `C:\Users\...`.
- **Line endings.** Write the log in UTF-8 with `\n`. Don't emit `\r\n` even on Windows; most editors render `\n` fine.
- **Shell.** Don't assume bash. Prefer language-native APIs over shelling out. When you must shell out, provide both a Unix and a Windows form.
- **Tool-specific extras.** This file is the canonical source. If a tool (Claude Code, Cursor, etc.) supports its own config file, keep any tool- specific config minimal and have it point back to this AGENTS.md rather than duplicating rules.
- **Nested AGENTS.md.** If a sub-project adds its own AGENTS.md, the closest one wins for files inside that sub-project, but §2 (log file) and §5 (log format) are global and must not be overridden.

---

## 8. QUICK CHECKLIST FOR THE AGENT

Before you respond to any user message, confirm:

- [ ] I have read this file in this session.

If any box is unchecked, fix that first.

# FlowGenius — MVP Product Requirements Document (PRD)

---

## 1. Project Overview  
FlowGenius is a **terminal-based AI learning assistant** that turns a plain-text goal (e.g., “learn microtonal guitar theory”) into an actionable, adaptive learning path saved as Markdown files. It removes research paralysis by scaffolding *Units → Resources → Engage Tasks*, all generated via OpenAI models orchestrated with LangChain and stored locally for Obsidian-friendly use.

---

## 2. User Roles & Core Workflows

1. **Learner** – Starts a new project, answers *what* and *why*, receives a structured plan, and iterates by marking progress or asking for refinements.  
2. **CLI Operator** – Runs FlowGenius commands (`wizard`, `new`, `plan`, `unit`, etc.) and configures global settings.

---

## 3. Technical Foundation

### 3.1 Data Models  
| Model | Fields | Notes |
|-------|--------|-------|
| **Config** | `openai_key_path`, `projects_root`, `link_style`, `default_model` | YAML at `$XDG_CONFIG_HOME/flowgenius/config.yaml`. |
| **Project** | `id`, `title`, `purpose`, `units[]`, `created_at` | Folder under `projects_root`; one project = one learning topic. |
| **Unit** | `index`, `title`, `objective`, `resources[]`, `engage_task`, `status` | Stored as `unitXX.md`. |
| **State** | `current_unit`, `completed_units[]`, `notes` | `state.json` inside each project folder. |

### 3.2 CLI Commands (Public API)
| Command | Args | Auth | Description |
|---------|------|------|-------------|
| `flowgenius wizard` | – | – | First-run config wizard. |
| `flowgenius new "<topic>"` | optional `--why` | Config present | Creates project folder and scaffolds units. |
| `flowgenius plan` | – | Project context | Prints table of contents (`toc.md`). |
| `flowgenius unit <n>` | flags: `--show`, `--mark-done`, `--refine` | Project context | Displays or updates a specific unit. |
| `flowgenius config` | `--edit`, `--show` | – | View or edit global config. |

### 3.3 Key Components
1. **CLI Entrypoint** – Click/Typer wrapper; dispatches commands.  
2. **Conversation Manager** – LangChain `ConversationBufferMemory`; routes user intents.  
3. **Topic Scaffolder Agent** – LLM chain → ordered Units (JSON).  
4. **Resource Curator Agent** – Fills each Unit with 3–5 links + summaries.  
5. **Engage Task Generator** – Adds quiz/project prompt per Unit.  
6. **Renderer** – Writes `toc.md`, `unitXX.md`; respects `link_style`.  
7. **State Store** – `state.json` for progress; optional SQLite checkpoint later.  
8. **Config Loader** – `platformdirs` + `pydantic-settings`; supports secrets file path.  
9. **(Optional)** Textual TUI – Async chat view over the same commands.

### 3.4 Tech Stack Summary
- **Language:** Python 3.12  
- **Packages:** `openai`, `langchain-core`, `langchain-openai`, `click` (or `typer` overlay), `platformdirs`, `pydantic-settings`, `ruamel.yaml`, `textual` (optional).  
- **Env:** Nix flake devShell; secrets injected via file path (`/run/secrets/openai.key`).  
- **Storage:** Local Markdown + JSON; no external DB in MVP.

---

## 4. MVP Launch Requirements (Must-Haves)

1. **Config Wizard** – Generates valid YAML and creates root project directory.  
2. **`new` Command** – Prompts for *topic* and *why*, produces at least 3 Units and writes `toc.md` + `unitXX.md`.  
3. **Resource & Task Generation** – Each Unit contains ≥1 video link, ≥1 reading link, and a concise Engage task.  
4. **Markdown Output** – Obsidian-compatible links; all files saved in project folder.  
5. **Progress Tracking** – `unit --mark-done` updates `state.json` and toggles status in Markdown.  
6. **Refinement Loop** – `unit --refine` re-calls agents to update that Unit based on user feedback.  
7. **Offline-safe Storage** – No cloud dependency; works entirely with local files + OpenAI API.  
8. **Nix Dev Shell** – `nix develop` brings up reproducible environment with all dependencies.  
9. **README** – Quick-start instructions and flake usage documented.  
10. **Demo Script** – Steps to create a project and walk through one Unit (for course evaluation).

---

## 5. Out-of-Scope for MVP (Phase 2+)

- Rich TUI navigation (Textual panes, keybindings beyond minimal).  
- Obsidian plug-in for in-app interaction.  
- Automated web scraping for full-text resources.  
- Scheduling / spaced-repetition reminders.  
- Collaborative or multi-user features.

---

## 6. Success Metrics

| Metric | Target at MVP Demo |
|--------|-------------------|
| End-to-end CLI run time for new topic | ≤ 60 s with GPT-4o-mini |
| Units generated contain working links | ≥ 80 % validity (manual spot-check) |
| Learner feedback workflow | One refine cycle completes without error |
| Dev setup reproducibility | `nix develop && flowgenius wizard` works on a clean machine |

---

**Owner:** *Batuhan*  

---

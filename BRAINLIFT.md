# FlowGenius — BrainLift Summary

---

## 1. Purpose

**Mission Statement:**  
Build a terminal-based AI learning assistant that  
**eliminates research paralysis** by taking a freeform learning goal  
(e.g., “learn microtonal guitar theory”) and producing a structured,  
adaptive learning plan composed of modular units, curated resources,  
and engagement tasks — all saved as local Markdown files  
for long-term knowledge retention and Obsidian integration.

**Why it matters:**  
Existing tools (Notion, Obsidian) help organize *what you already know*,  
but they don't help when you’re stuck at the starting line.  
FlowGenius provides **direction before organization**,  
removing the friction of figuring out what to learn and how to begin.

---

## 2. SpikyPOVs (Myths vs. Truths)

| **Myth (Consensus Thinking)** | **Truth (Your Experience)** |
|------------------------------|-----------------------------|
| Learning is about collecting as much information as possible. | Learning is about **building connected mental models** and practicing the skill, not just accumulating facts. |
| Tools like Notion and Obsidian help you learn if you're organized enough. | If you don't know **what** to organize, you’ll just create structured garbage — like practicing poor gym form and getting good at being wrong. |
| More content = better learning. | **Direction and relevance** matter more than volume. You need to know *why* and *in what order* to learn something. |
| Freedom sparks motivation and creativity. | **Freedom at the beginning creates paralysis**. Constraint and scaffolding are essential early on. Freedom comes *after* foundations are built. |
| You can just figure it out by Googling enough. | The internet gives you information, not structure. **Teachers, mentors, and now AI agents** exist to scaffold your path. |

---

## 3. Knowledge Tree

### 3.1 Learning Targets

FlowGenius should support both **skill acquisition** and **theoretical understanding**, including:

- Music theory → for composition, appreciation, and playing microtonal guitar  
- Coding languages → contextual learning based on purpose or project  
- Math & physics → revisited for personal growth, overcoming bad instruction  
- Fitness / gym knowledge → to improve technique, performance, and safety  
- AI/LLMs → applied learning in real-time with project constraints

### 3.2 Ideal Input Format

- Conversational, natural language:  
  *"I want to learn about X."*  
- Assistant asks:  
  *“Why do you want to learn this?”*  
- No need for structured forms; back-and-forth chat is preferred.

### 3.3 What Makes a Good Learning Path

- **Scaffolded Units**:  
  Clear titles, logical progression  
- **Curated Resources**:  
  YouTube videos, articles, papers, docs —  
  so you don’t waste time searching  
- **Engage Tasks**:  
  Reflection, quizzes, or mini-projects per unit  
  to deepen understanding  
- **Adaptivity**:  
  If you struggle, the assistant adjusts future units accordingly  
- **Stored as Markdown**:  
  Obsidian-compatible, readable offline

### 3.4 Format Preferences

- Text-first (terminal UI)  
- Files saved as structured Markdown (`toc.md`, `unitXX.md`)  
- Folder-based project structure (`~/Learning/<topic>/...`)  
- Config stored in `$XDG_CONFIG_HOME/flowgenius/config.yaml`  
- Obsidian-style (wiki-style + yaml frontmatter) or markdown-style links (user preference)

### 3.5 Where Help is Needed Most

- Turning vague learning goals into **structured, sequential learning paths**  
- **Finding meaningful resources** without overwhelming the user  
- **Creating engagement tasks** that encourage practice, not just passive reading  
- **Reducing decision fatigue**, especially at the start of a new topic  
- Storing all output in local files —  
  no vendor lock-in or cloud storage required

---

# FlowGenius

AI-assisted learning assistant that eliminates research paralysis by transforming freeform learning goals into structured, adaptive learning plans.

## Description

FlowGenius helps you break through the overwhelming choice paralysis that comes with learning something new.
Instead of spending hours figuring out *what* to learn and *how* to begin, simply tell FlowGenius your learning goal and get:

- 📚 **Structured Learning Units** with clear progression
- 🔗 **Curated Resources** (videos, articles, papers) 
- 🎯 **Engaging Tasks** for active learning
- 📝 **Local Markdown Files** for long-term retention
- 🔄 **Adaptive Planning** that adjusts based on your progress

All content is saved locally as Markdown files, perfect for Obsidian integration and lifetime knowledge retention.

## Quick Start

### 1. Installation & Setup

This flake provides a `home-manager` module. For more info, see [`nix/README.md`](nix/README.md) 
Alternatively, use your favourite package manager.

```bash
pip --user install flowgenius

# Configure your environment
flowgenius wizard

# Create your first learning project
flowgenius new "Learn NixOS"
```

## Usage

```bash
# Interactive configuration wizard
flowgenius wizard

# Create a new learning project
flowgenius new "learn Python data structures"
flowgenius new "understand quantum computing basics"

# Start with a specific motivation
flowgenius new "learn Rust programming" --why "build fast CLI tools"

# List your projects
flowgenius list

# Continue working on a project  
flowgenius continue quantum-computing-basics-001
```

## Configuration

FlowGenius stores configuration in `$XDG_CONFIG_HOME/flowgenius/config.yaml` (typically `~/.config/flowgenius/config.yaml`).

### Configuration Options

- **`openai_key_path`**: Path to your OpenAI API key file
- **`projects_root`**: Directory where learning projects are stored  
- **`link_style`**: "obsidian" (wiki-style) or "markdown" (standard) links
- **`default_model`**: OpenAI model for content generation (default: gpt-4o-mini)

### Setup Methods

1. **Interactive Wizard** (recommended for first-time users):
   ```bash
   flowgenius wizard
   ```

2. **Home Manager Module** (recommended for Nix users):
   ```nix
   programs.flowgenius.enable = true;
   ```
   See [`nix/README.md`](nix/README.md) for complete documentation.

3. **Manual Configuration**: Edit `~/.config/flowgenius/config.yaml` directly

## Development

### Prerequisites

- Nix (recommended) or Python 3.13+
- OpenAI API key

### Nix Development

```bash
# Enter development shell with all dependencies
nix develop

# FlowGenius is available in editable mode
flowgenius --help

# Run tests
python -m pytest

# Format code  
black src/ tests/
```

### Traditional Python Development

```bash
# Install with uv (recommended)
uv sync
source .venv/bin/activate

# Or with pip
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Project Structure

```
flowgenius/
├── src/flowgenius/
│   ├── cli/           # Command-line interface
│   ├── agents/        # AI agents for content generation
│   ├── models/        # Pydantic data models
│   └── renderers/     # Markdown file generation
├── nix/               # Nix integration (home-manager module)
├── tests/             # Test suite
└── docs/              # Documentation
```

## Architecture

FlowGenius uses a modular architecture:

- **CLI Layer**: Click-based commands (`flowgenius wizard`, `flowgenius new`)
- **Agent Layer**: Specialized AI agents for different tasks
  - Topic Scaffolder: Creates learning unit structure
  - Resource Curator: Finds relevant learning materials  
  - Task Generator: Creates engaging learning activities
- **Model Layer**: Pydantic models for type safety and validation
- **Storage Layer**: Local file system with Markdown output

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

### Code Standards

- **Type hints** for all functions
- **Docstrings** for modules, classes, and functions
- **Tests** for new functionality
- **Black** formatting
- **Files ≤ 500 lines** for AI tool compatibility

## License

MIT License - see [LICENSE](LICENSE) for details.

## Roadmap

- [ ] **Task 3**: `flowgenius new` command with AI project generation
- [ ] **Task 4**: Resource curation with real web links
- [ ] **Task 5**: Markdown rendering with proper link styles
- [ ] **Task 6**: Progress tracking and state management
- [ ] **Task 7**: Refinement loop for iterative improvement
- [ ] **Task 8**: Offline-safe operation
- [ ] **Task 9**: Enhanced Nix dev shell
- [ ] **Task 10**: Documentation and demo script

*Current Status: 2/10 tasks complete* ✅ ✅ ⏳ ⏳ ⏳ ⏳ ⏳ ⏳ ⏳ ⏳
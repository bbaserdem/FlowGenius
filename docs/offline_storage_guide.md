# FlowGenius Offline Storage Guide

This guide explains how FlowGenius maintains offline functionality and ensures secure local storage of your learning data.

## Table of Contents
- [Overview](#overview)
- [Storage Architecture](#storage-architecture)
- [Offline Functionality](#offline-functionality)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)
- [Developer Guidelines](#developer-guidelines)

## Overview

FlowGenius is designed as an offline-first application that stores all data locally on your machine. The only network requirement is for OpenAI API calls when generating learning content.

### Key Principles
- **Local-First:** All data stored on your filesystem
- **Privacy-Focused:** No cloud storage or tracking
- **Secure:** API keys protected with strict file permissions
- **Portable:** Standard file formats (JSON, Markdown, YAML)

## Storage Architecture

### Directory Structure
```
~/                                    # Your home directory
├── .config/                          
│   └── flowgenius/                   # FlowGenius configuration (XDG standard)
│       ├── config.yaml               # Application settings
│       └── openai_key.txt            # API key (chmod 600)
│
├── .secrets/                         # Alternative secure location
│   └── openai_api_key                # API key (chmod 600)
│
└── Documents/
    └── FlowGenius/                   # Default projects root (XDG_DOCUMENTS_DIR)
        └── python-basics-a1b2c3d4/   # Example project
        ├── project.json              # Project metadata
        ├── state.json                # Progress tracking
        ├── toc.md                    # Table of contents
        ├── README.md                 # Quick start guide
        ├── units/                    # Learning units
        │   ├── unit-1.md
        │   └── unit-2.md
        ├── resources/                # Additional materials
        ├── notes/                    # Personal notes
        └── .refinement_backups/      # Backup history
```

### File Types and Purposes

| File | Purpose | Format |
|------|---------|--------|
| `config.yaml` | Application settings | YAML |
| `project.json` | Project structure and metadata | JSON |
| `state.json` | Progress tracking | JSON |
| `*.md` | Learning content | Markdown |
| `openai_key.txt` | API key | Plain text |

## Offline Functionality

### What Works Offline
✅ **Full Functionality:**
- Viewing existing projects
- Reading learning materials
- Tracking progress
- Managing task status
- Creating backups
- Refining content (if already generated)

✅ **Partial Functionality:**
- Configuration management
- File operations
- State persistence

### What Requires Internet
❌ **OpenAI API Calls:**
- Creating new projects (`flowgenius new`)
- Generating learning content
- AI-powered refinements
- Content expansion

### Testing Offline Mode
```bash
# Disconnect from internet, then:
cd ~/Documents/FlowGenius/your-project
cat toc.md                    # View content
cat units/unit-1.md          # Read units
cat state.json               # Check progress
```

## Security Best Practices

### 1. API Key Protection

**Store your API key securely:**
```bash
# Create secure directory
mkdir -p ~/.secrets
chmod 700 ~/.secrets

# Save API key with restricted permissions
echo "sk-your-api-key" > ~/.secrets/openai_api_key
chmod 600 ~/.secrets/openai_api_key
```

**Never:**
- Commit API keys to version control
- Store keys in cloud-synced folders
- Share keys in documentation

### 2. File Permissions

**Recommended permissions:**
```bash
# API key files
chmod 600 ~/.secrets/openai_api_key

# Configuration directory
chmod 700 ~/.config/flowgenius

# Project directories (optional)
chmod 755 ~/Documents/FlowGenius/project-name
```

### 3. Backup Security

**Secure your backups:**
```bash
# Exclude from cloud sync
echo ".refinement_backups/" >> ~/.gitignore

# Or encrypt sensitive backups
tar -czf - .refinement_backups/ | gpg -c > backups.tar.gz.gpg
```

### 4. Multi-User Systems

On shared systems:
- Use restrictive umask: `umask 077`
- Store projects in user-only directories
- Consider encrypted home directories

## Troubleshooting

### Common Issues

**"API key file not found"**
```bash
# Check file exists
ls -la ~/.config/flowgenius/openai_key.txt

# Verify permissions
stat -c %a ~/.config/flowgenius/openai_key.txt  # Should be 600

# Re-run wizard if needed
flowgenius wizard
```

**"Network error" when offline**
- This is expected for content generation
- Use existing projects offline
- Generate content while online, use offline

**Permission denied errors**
```bash
# Fix API key permissions
chmod 600 ~/.config/flowgenius/openai_key.txt

# Fix directory permissions
chmod 755 ~/Documents/FlowGenius
```

## Developer Guidelines

### Adding New Features

**Maintain offline compatibility:**
```python
# Good: Local file operation
def save_progress(data, path):
    with open(path, 'w') as f:
        json.dump(data, f)

# Good: Graceful network failure
def generate_content(unit):
    try:
        return api_call(unit)
    except NetworkError:
        return fallback_content(unit)
```

**Avoid cloud dependencies:**
```python
# Bad: Cloud storage
def save_to_cloud(data):
    cloud_client.upload(data)  # Don't do this

# Bad: Required network checks
def load_project():
    if not check_internet():
        raise Error("Internet required")  # Don't do this
```

### Security Checklist

When adding features:
- [ ] No hardcoded secrets
- [ ] Sensitive files get 600 permissions
- [ ] No sensitive data in logs/errors
- [ ] Path validation prevents traversal
- [ ] Input validation on all user data

### Testing Offline Mode

```python
# tests/test_offline_functionality.py
def test_feature_works_offline():
    with patch('socket.socket') as mock:
        mock.side_effect = socket.error("Network unavailable")
        # Test your feature
        assert feature_works()
```

## Best Practices Summary

### For Users
1. **Secure Storage:** Keep API keys in protected directories
2. **Regular Backups:** Backup your Learning directory
3. **Offline Planning:** Generate content while online for offline use
4. **Permission Check:** Verify 600 on API key files

### For Developers
1. **Local-First Design:** Always prefer local operations
2. **Graceful Failures:** Network errors should not break the app
3. **Security by Default:** Enforce permissions programmatically
4. **Clear Documentation:** Document any network requirements

## Appendix: Environment Setup

### NixOS Users
```nix
programs.flowgenius = {
  enable = true;
  openaiKeyPath = "${config.home.homeDirectory}/.secrets/openai_api_key";
  projectsRoot = "${config.home.homeDirectory}/Learning";
};
```

### Standard Setup
```bash
# Install
pip install flowgenius

# Configure
flowgenius wizard

# Verify offline functionality
python -m pytest tests/test_offline_functionality.py
```

---

Remember: FlowGenius respects your privacy by keeping all your learning data local. The only external communication is with OpenAI's API for content generation, and even that is optional once your content is created. 
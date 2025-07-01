# Changelog - OpenAI Whisper Web Interface

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-rc1] - 2025-07-01

### 🎯 **MAJOR REFACTORING - Release Candidate 1**

This release represents a complete architectural overhaul and project reorganization. The application has been modernized from a complex multi-deployment system to a focused, production-ready web interface for OpenAI Whisper.

### Added - NEW FEATURES 🆕
- **🎤 Unified Flask Application**: Single `main.py` with modular architecture
- **📁 Organized Project Structure**: Clear separation of scripts, docs, and legacy code
- **🐳 Docker-Ready Architecture**: Prepared for containerization (Docker support coming)
- **🔧 Modernized Development Tools**: Updated `dev.sh` script for current Flask app
- **📚 Complete Documentation Rewrite**: New README, ARCHITECTURE, and guides
- **🎯 Clear Deployment Strategy**: Focus on Proxmox LXC and Docker containers
- **🔄 Release Candidate Versioning**: Proper semantic versioning for testing phase

### Changed - MAJOR IMPROVEMENTS ⚡
- **📦 Project Renamed**: "Enhanced WhisperS2T Appliance" → "OpenAI Whisper Web Interface"
- **🏗️ Architecture Simplified**: From FastAPI + multiple backends → Flask + SocketIO
- **📂 File Organization**: Scripts moved to `scripts/`, docs reorganized
- **🔄 Development Workflow**: Updated for Flask-based development
- **📊 Documentation Focus**: Clear deployment paths instead of multiple confusing options
- **🎯 Single Source of Truth**: One main application instead of multiple variants

### Moved - REORGANIZATION 📁
- **📜 Legacy Documentation**: Moved to `docs/legacy/` (README-v0.9.md, ARCHITECTURE-v0.9.md, CHANGELOG-v0.9.md)
- **🏗️ ISO Builders**: Moved to `scripts/legacy/` (build_full_iso.sh, build-live-iso.sh)
- **🔧 Development Tools**: Moved to `scripts/` (dev.sh, debug-container.sh, test-container.sh)
- **📚 Fedora Build Docs**: Moved to `docs/legacy/FEDORA-BUILD-SETUP.md`

### Marked as Legacy - DEPRECATED ⚠️
- **💿 ISO Building**: All ISO builders marked as experimental/legacy
- **🔧 Fedora Live Build**: Complex livemedia-creator approach deprecated
- **📦 Multiple Deployment Methods**: Focus on Docker + Proxmox only
- **⚙️ FastAPI Backend**: Replaced with Flask + SocketIO for simplicity

### Fixed - TECHNICAL IMPROVEMENTS 🛠️
- **🔧 Development Server**: Updated for Flask instead of FastAPI
- **📍 Port Configuration**: Standardized on HTTPS port 5001
- **🔐 SSL Certificate Handling**: Better network IP support
- **📦 Dependency Management**: Cleaner requirements for Flask stack
- **🎯 Project Paths**: Fixed relative paths in dev.sh script

### Technical Details 🔧

#### **New Project Structure**
```
whisper-appliance/
├── src/                     # Main application (Flask)
├── scripts/                 # All deployment/dev scripts
│   └── legacy/             # Deprecated ISO builders
├── docs/                   # Current documentation
│   └── legacy/             # v0.9.0 documentation
├── ssl/                    # SSL certificates
└── README.md               # New focused documentation
```

#### **Development Changes**
- **Framework**: FastAPI → Flask + SocketIO
- **Port**: 5000 → 5001 (HTTPS)
- **Development**: `./scripts/dev.sh dev start`
- **Architecture**: Modular Flask components

#### **Deployment Focus**
1. **Primary**: Proxmox LXC containers (one-line installer)
2. **Secondary**: Docker containers (coming in stable release)
3. **Development**: Local Flask server
4. **Legacy**: ISO builds (experimental only)

### Migration Guide 📋

#### **For Developers**
```bash
# Update development workflow
git pull origin main
./scripts/dev.sh dev start    # New command for Flask app

# Old FastAPI paths no longer work
# New: src/main.py (Flask)
# Old: src/webgui/backend/ (FastAPI)
```

#### **For Deployments**
```bash
# Proxmox deployment unchanged
bash <(curl -s https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/scripts/proxmox-standalone.sh)

# Docker deployment (coming soon)
docker-compose up -d
```

#### **Documentation Updates**
- **New README**: Focus on Docker + Proxmox
- **Legacy Docs**: Available in `docs/legacy/`
- **Architecture**: Completely rewritten for Flask

### Known Issues ⚠️

#### **Release Candidate Limitations**
- **🚧 Production Readiness**: Needs testing before stable v1.0.0
- **🐳 Docker Support**: Dockerfile and docker-compose.yml coming
- **📊 Performance Testing**: Large-scale deployment testing needed
- **🔧 Feature Completeness**: Some v0.9.0 features may need verification

#### **Testing Needed**
- [ ] All Whisper models load correctly
- [ ] WebSocket live speech works reliably
- [ ] File upload handles all audio formats
- [ ] SSL certificates work across network
- [ ] Container deployment functions properly
- [ ] Update system maintains compatibility

### Breaking Changes 💥

#### **File Paths**
- `./dev.sh` → `./scripts/dev.sh`
- `src/webgui/backend/` → `src/` (Flask app)
- Documentation files moved to new locations

#### **API Endpoints**
- Port changed from 5000 to 5001
- HTTPS required (was optional)
- Some endpoint paths may have changed

#### **Development Workflow**
- Virtual environment setup changed
- Dependency installation process updated
- Different main script execution

### Upgrade Instructions 🔄

#### **From v0.9.0**
```bash
# Backup current installation
cp -r whisper-appliance whisper-appliance-v0.9.0-backup

# Pull latest changes
cd whisper-appliance
git pull origin main

# Update development environment
./scripts/dev.sh dev setup

# Test new Flask application
./scripts/dev.sh dev start
```

#### **Container Deployments**
```bash
# Container deployments should auto-update
# Manual update if needed:
./auto-update.sh
```

### Feedback Needed 📝

This is a **Release Candidate** - we need your feedback before the stable v1.0.0 release:

1. **🧪 Testing**: Try the new Flask application
2. **📦 Deployment**: Test container installations
3. **🐛 Bug Reports**: Report any issues on GitHub
4. **💡 Feature Requests**: Suggest improvements
5. **📚 Documentation**: Report unclear documentation

### Next Steps → v1.0.0 🚀

#### **Planned for Stable Release**
- [ ] **🐳 Docker Support**: Complete Docker container implementation
- [ ] **✅ Comprehensive Testing**: All features verified working
- [ ] **📊 Performance Optimization**: Memory and CPU usage optimization
- [ ] **🔧 Production Hardening**: Security audit and improvements
- [ ] **📚 Complete Documentation**: User guides and deployment documentation

#### **Timeline**
- **v1.0.0-rc2**: Bug fixes and Docker support
- **v1.0.0**: Stable production release

---

## [0.9.0] - 2025-06-30 (LEGACY)

**Note**: v0.9.0 documentation and features available in `docs/legacy/`

### Legacy Features (Preserved)
- Enhanced modular architecture with live speech and upload handling
- Intelligent Network SSL with SAN support
- Proxmox container deployment
- Admin panel with model management
- Chat history database
- Web-based update system

**Full v0.9.0 changelog**: See `docs/legacy/CHANGELOG-v0.9.md`

---

## Contributing 🤝

We welcome feedback and contributions, especially during the Release Candidate phase:

- **🐛 Bug Reports**: [GitHub Issues](https://github.com/GaboCapo/whisper-appliance/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/GaboCapo/whisper-appliance/discussions)
- **🔧 Pull Requests**: Follow [Contributing Guidelines](CONTRIBUTING.md)
- **📖 Documentation**: Help improve docs and guides

## Release Philosophy 📋

- **Release Candidates (-rc)**: Testing versions, not production ready
- **Stable Releases (x.y.z)**: Production ready, thoroughly tested
- **Legacy Support**: Previous versions documented and preserved
- **Breaking Changes**: Clearly documented with migration guides

---

**🎉 Thank you for testing OpenAI Whisper Web Interface v1.0.0-rc1!**

Your feedback helps us build a better speech-to-text solution.

# Changelog

All notable changes to VPS Provisioner will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.1] - 2025-12-08

### Fixed
- n8n installation permission errors (EACCES on /home/node/.n8n/config)
  - Added proper permissions for n8n data directory (UID 1000)
  - Fixed with `chown -R 1000:1000` and `chmod -R 755`
- n8n Safari cookie security warning
  - Added `N8N_SECURE_COOKIE=false` environment variable
  - Allows HTTP access without HTTPS redirect

## [2.1.0] - 2025-12-03

### Added
- **Universal Provisioner** - Install ANY Docker application
  - Support for 3 source types:
    - `docker-compose` - from docker-compose.yml URL
    - `docker-image` - from Docker Hub or registry
    - `github-repo` - clone, build, and run from GitHub
  - Automatic resource checking (RAM, disk, CPU, ports)
  - Smart safety limits to prevent server crashes
  - Port conflict detection
  - Security checks (privileged mode, host network, etc)
- New endpoint: `POST /provision/universal`
- Resource checker module (`resource_checker.py`)
- Docker Compose parser with safety limits (`compose_parser.py`)
- Comprehensive documentation:
  - `UNIVERSAL_PROVISIONER_GUIDE.md` - complete usage guide
  - `TEST_CASES.md` - 25+ detailed test cases
  - `PROJECT_IMPROVEMENT_RECOMMENDATIONS.md` - improvement roadmap

### Changed
- Updated README with Universal Provisioner info
- Added PyYAML and requests to dependencies

## [2.0.0] - 2025-11-XX

### Added
- Initial release
- Pre-configured provisioners for 7 applications:
  - n8n - Workflow automation
  - WireGuard - VPN with UI
  - Outline - Wiki/documentation
  - Vaultwarden - Password manager
  - 3X-UI - Advanced VPN panel
  - FileBrowser - File manager
  - Seafile - File sync and share
- REST API with endpoints:
  - `POST /provision` - Install pre-configured app
  - `GET /status/<job_id>` - Check installation status
  - `GET /jobs` - List all jobs
  - `GET /stats` - Get statistics
  - `POST /cleanup` - Clean old jobs
  - `GET /health` - Health check
- API key authentication
- SQLite job storage
- Async job processing with threading
- SSH-based remote installation
- Gunicorn production support
- Systemd service configuration

---

## Version Format

**MAJOR.MINOR.PATCH**

- **MAJOR** - Breaking changes, incompatible API changes
- **MINOR** - New features, backwards compatible
- **PATCH** - Bug fixes, backwards compatible

## Links

- [Repository](https://github.com/technoob228/vps)
- [Issues](https://github.com/technoob228/vps/issues)

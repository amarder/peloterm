# Contributing to Peloterm

Thank you for your interest in contributing to Peloterm! This guide will help you get started with development, understand the project structure, and submit pull requests.

## 📁 Project Structure

```
peloterm/
├── peloterm/              # Python package
│   ├── web/
│   │   ├── static/        # Built Vue files (auto-generated)
│   │   └── server.py      # FastAPI backend
│   ├── devices/           # Bluetooth device handlers
│   ├── cli.py             # Terminal interface
│   └── ...                # Other Python modules
├── frontend/              # Vue 3 web interface
│   ├── src/
│   │   ├── components/    # Vue components
│   │   ├── composables/   # Reusable logic
│   │   └── types/         # TypeScript definitions
│   ├── package.json
│   └── vite.config.ts
├── build.py               # Build frontend → Python package
├── dev.py                 # Development server runner
└── pyproject.toml         # Python package configuration
```

## 🚀 Development Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- Git

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/peloterm.git
   cd peloterm
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

## 🛠 Development Workflow

### Quick Start (Recommended)

For most development work, use the unified development server:

```bash
# Run both Vue dev server + FastAPI backend
python dev.py
```

This provides:
- Vue UI: http://localhost:5173 (with hot reload)
- FastAPI: http://localhost:8000
- Automatic proxy setup between frontend and backend

### Frontend Development

For frontend-focused work:

```bash
# Terminal 1: Run backend
python -m peloterm.web.server

# Terminal 2: Run frontend with proxy
cd frontend
npm run dev
```

### Backend Development

For backend-focused work:

```bash
# Run just the FastAPI server
python -m peloterm.web.server
```

### Building for Production

```bash
# Build frontend into Python package
python build.py

# Test production build
python dev.py prod
```

## 🏗 Architecture

### Backend (Python)

- **FastAPI** web server with WebSocket support
- **Bluetooth** device communication using `bleak`
- **Real-time** metrics processing
- **Configuration** management
- **FIT file** generation for ride recording
- **Strava API** integration

Key modules:
- `peloterm/cli.py` - Command-line interface
- `peloterm/web/server.py` - Web server and API
- `peloterm/devices/` - Bluetooth device handlers
- `peloterm/strava/` - Strava integration
- `peloterm/recording/` - Ride recording and FIT file generation

### Frontend (Vue 3)

- **Component-based** architecture with TypeScript
- **Chart.js** for real-time visualizations
- **Responsive** design with mobile support
- **WebSocket** connection for real-time data
- **Hot reload** development

Key directories:
- `frontend/src/components/` - Vue components
- `frontend/src/composables/` - Reusable logic
- `frontend/src/types/` - TypeScript definitions

### Build Process

1. Vue builds optimized production files using Vite
2. `build.py` copies files to `peloterm/web/static/`
3. FastAPI serves the built files as static assets
4. Single Python command runs everything in production

## 🧪 Testing

### Python Tests

```bash
# Run all Python tests
pytest

# Run with coverage
pytest --cov=peloterm

# Run specific test file
pytest tests/test_devices.py
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
npm run test:unit

# Run tests in watch mode
npm run test:unit -- --watch

# Run with coverage
npm run test:unit -- --coverage
```

### Integration Tests

```bash
# Test the full build process
python build.py
python dev.py prod
# Verify http://localhost:8000 works correctly
```

## 📦 Distribution

The build process creates a self-contained Python package:
- All frontend assets bundled into the package
- No separate frontend server needed in production
- Single `pip install` for end users
- Automatic static file serving via FastAPI

## 🎯 Advanced Features

### Command Options

The `peloterm start` command supports many options:

- `--config PATH` - Use a specific configuration file
- `--timeout 60` - Set connection timeout in seconds (default: 60)
- `--debug` - Enable debug output
- `--web/--no-web` - Enable/disable web UI (default: enabled)
- `--port 8000` - Set web server port
- `--duration 30` - Set target ride duration in minutes
- `--no-recording` - Disable automatic ride recording

### Strava Integration

Peloterm includes comprehensive Strava integration:

```bash
# Set up Strava (interactive)
peloterm strava setup

# Test connection
peloterm strava test

# List recorded rides
peloterm strava list

# Upload specific ride
peloterm strava upload ride_file.fit --name "Epic Ride"
```

### File Formats

Peloterm generates **FIT files** for ride recording:
- ✅ **Compact**: Binary format, smaller than TCX/GPX
- ✅ **Complete**: Supports all cycling metrics
- ✅ **Compatible**: Works with Garmin devices and most apps
- ✅ **Strava-optimized**: Best format for Strava uploads

Files are saved to `~/.peloterm/rides/`

## 🔧 Configuration

### Development Configuration

Create a `.env` file in the project root:

```env
DEBUG=true
LOG_LEVEL=debug
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
```

### Device Configuration

Device configuration is stored in `~/.peloterm/config.json`:

```json
{
  "devices": {
    "heart_rate": "AA:BB:CC:DD:EE:FF",
    "power_meter": "11:22:33:44:55:66",
    "cadence": "77:88:99:AA:BB:CC"
  },
  "web": {
    "iframe_url": "https://www.youtube.com/embed/VIDEO_ID",
    "port": 8000
  }
}
```

## 📈 Performance Considerations

### Frontend Optimization

- **Tree-shaking** removes unused code
- **Asset optimization** and caching
- **Efficient reactivity** with Vue 3 Composition API
- **WebSocket** for low-latency data updates

### Backend Optimization

- **Async/await** for non-blocking operations
- **Efficient Bluetooth** scanning and connection
- **Minimal memory** footprint for long rides
- **Graceful error handling** and reconnection

## 🤝 Contributing Guidelines

### Code Style

**Python:**
- Follow PEP 8
- Use `black` for formatting: `black .`
- Use `isort` for imports: `isort .`
- Type hints are encouraged

**TypeScript/Vue:**
- Follow Vue 3 style guide
- Use Prettier for formatting: `npm run format`
- Use ESLint: `npm run lint`

### Commit Messages

Use conventional commits:
- `feat:` new features
- `fix:` bug fixes
- `docs:` documentation changes
- `style:` formatting changes
- `refactor:` code refactoring
- `test:` adding tests
- `chore:` maintenance tasks

Examples:
```
feat: add power meter support for Wahoo devices
fix: resolve WebSocket connection timeout issue
docs: update installation instructions
```

### Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes
4. **Add** tests for new functionality
5. **Run** the test suite: `pytest && cd frontend && npm test`
6. **Commit** your changes with conventional commit messages
7. **Push** to your fork: `git push origin feature/amazing-feature`
8. **Open** a Pull Request

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional format
- [ ] No breaking changes (or clearly documented)
- [ ] Frontend builds successfully (`python build.py`)

## 🐛 Debugging

### Common Issues

**Bluetooth connection problems:**
```bash
# Enable debug mode
peloterm start --debug

# Check device permissions (Linux)
sudo usermod -a -G dialout $USER
```

**Frontend build issues:**
```bash
# Clear node modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Clear build cache
rm -rf peloterm/web/static/*
python build.py
```

**WebSocket connection issues:**
- Check firewall settings
- Verify port 8000 is available
- Try different port: `peloterm start --port 8001`

### Development Tools

- **Vue DevTools** browser extension for frontend debugging
- **FastAPI docs** at http://localhost:8000/docs for API testing
- **WebSocket testing** tools for real-time connection debugging

## 📚 References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue 3 Documentation](https://vuejs.org/)
- [Chart.js Documentation](https://www.chartjs.org/)
- [Bleak (Bluetooth) Documentation](https://bleak.readthedocs.io/)
- [FIT SDK Documentation](https://developer.garmin.com/fit/overview/)

### Related Projects

- [GoldenCheetah](https://github.com/goldencheetah/goldencheetah) - Cycling analytics
- [Endurain](https://github.com/joaovitoriasilva/endurain) - Self-hosted fitness tracking
- [PyCycling](https://github.com/zacharyedwardbull/pycycling) - Python cycling sensors library

## 📞 Getting Help

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Discord**: Join our community Discord server (link in README)

Thank you for contributing to Peloterm! 🚴‍♂️

# Peloterm

A terminal-based cycling metrics visualization tool with a modern web interface.

## 📁 Project Structure

```
bike/
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

## 🚀 Quick Start

### Development Mode (Hot Reload)
```bash
# Run both Vue dev server + FastAPI backend
python dev.py
```
- Vue UI: http://localhost:5173 (with hot reload)
- FastAPI: http://localhost:8000

### Production Mode
```bash
# Build frontend and run production server
python build.py
python dev.py prod
```
- Production server: http://localhost:8000

### Frontend Only
```bash
cd frontend
npm install
npm run dev
```

## 🛠 Development Workflow

### 1. Frontend Development
```bash
# Terminal 1: Run backend
python -m peloterm.web.server

# Terminal 2: Run frontend with proxy
cd frontend
npm run dev
```

### 2. Building for Production
```bash
# Build frontend into Python package
python build.py

# Verify build
python dev.py prod
```

### 3. One-Command Development
```bash
# Runs both servers together
python dev.py
```

## 🏗 Architecture

### Backend (Python)
- **FastAPI** web server with WebSocket support
- **Bluetooth** device communication
- **Real-time** metrics processing
- **Configuration** management

### Frontend (Vue 3)
- **Component-based** architecture
- **TypeScript** for type safety
- **Chart.js** for real-time visualizations
- **Responsive** design
- **Hot reload** development

### Build Process
1. Vue builds optimized production files
2. Files are automatically placed in `peloterm/web/static/`
3. FastAPI serves the built files
4. Single Python command runs everything

## 📦 Distribution

The build process creates a self-contained Python package:
- All frontend assets bundled into the package
- No separate frontend server needed in production
- Single `pip install` for end users

## 🎯 Features

- **Real-time Metrics**: Power, speed, cadence, heart rate
- **Interactive Charts**: Historical data visualization
- **Responsive Design**: Works on desktop and mobile
- **Resizable Panels**: Customizable layout
- **Dark Theme**: Easy on the eyes
- **WebSocket Updates**: Low-latency data streaming

## 🔧 Configuration

Configure iframe URL and metrics in the web interface or via config files.

## 📱 Web Interface

The Vue frontend provides:
- Real-time cycling metrics display
- Interactive Chart.js visualizations
- Resizable video panel
- Mobile-responsive design
- Dark theme matching terminal aesthetic

## 🧪 Testing

```bash
# Frontend tests
cd frontend
npm run test:unit

# Python tests
pytest
```

## 📈 Performance

- **Optimized builds** with Vite
- **Tree-shaking** removes unused code
- **Asset optimization** and caching
- **Efficient reactivity** with Vue 3

## Features

- Real-time BLE sensor connection with concurrent device scanning
- Modern web-based UI with configurable video integration (YouTube by default)
- Support for multiple sensor types
- Easy-to-use command line interface
- Automatic device reconnection if connection is lost
- Smart listening mode that waits for you to turn on devices - no more timing issues!
- **Automatic ride recording with FIT file generation**
- **Interactive Strava upload during shutdown**

## Installation

```bash
pip install peloterm
```

## Usage

First, scan for available Bluetooth sensors in your area:

```bash
peloterm scan
```

This will show all available BLE devices and help you set up your configuration file with the correct sensor IDs.

### Starting Your Session

```bash
peloterm start
```

**Perfect for devices that auto-sleep quickly!** By default, peloterm now uses smart listening mode:
- Shows you which devices it's waiting for
- Lets you turn on your devices when you're ready
- Connects to all devices concurrently as they become available
- Automatically starts monitoring once all devices are connected
- **Records your ride data automatically**

**Example workflow:**
1. Run `peloterm start`
2. See the list of devices it's waiting for
3. Turn on your heart rate monitor, cadence sensor, and trainer
4. Watch as each device connects in real-time
5. Start your workout once all devices are connected!
6. **Press Ctrl+C when done - you'll be prompted to save and upload your ride**

### Recording and Strava Integration

When you stop Peloterm (Ctrl+C), you'll be prompted with:

1. **💾 Save this ride as a FIT file?** - Save your ride data
2. **📝 Enter a name for your ride** - Optional custom name
3. **🚴 Upload this ride to Strava?** - Direct upload to Strava
4. **Activity details** - Name and description for Strava

If Strava isn't set up yet, you'll be guided through the setup process automatically.

### Strava Setup (Optional)

To set up Strava integration ahead of time:

```bash
peloterm strava setup
```

This will guide you through:
1. Creating a Strava API application
2. Authorizing Peloterm to upload activities
3. Storing your credentials securely

### Other Strava Commands

```bash
# Test your Strava connection
peloterm strava test

# List all recorded rides
peloterm strava list

# Upload a specific ride file
peloterm strava upload ride_file.fit --name "Epic Mountain Climb"
```

### Command Options

The `start` command supports these options:

- `--config PATH` - Use a specific configuration file
- `--timeout 60` - Set connection timeout in seconds (default: 60)
- `--debug` - Enable debug output
- `--web/--no-web` - Enable/disable web UI (default: enabled)
- `--port 8000` - Set web server port
- `--duration 30` - Set target ride duration in minutes
- `--no-recording` - Disable automatic ride recording

Examples:
```bash
# Standard ride with recording
peloterm start

# Disable recording (monitoring only)
peloterm start --no-recording

# Use debug mode to troubleshoot connections
peloterm start --debug

# Listen for devices with 2-minute timeout
peloterm start --timeout 120
```

## File Formats

When recording rides, Peloterm generates **FIT files** which are:
- ✅ **Compact**: Binary format, much smaller than TCX/GPX
- ✅ **Complete**: Supports all cycling metrics (power, cadence, heart rate, speed)
- ✅ **Compatible**: Native format for Garmin devices and widely supported
- ✅ **Strava-optimized**: Best format for uploading to Strava

FIT files are saved to `~/.peloterm/rides/` and can be uploaded to Strava or imported into other cycling apps.

## Development

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/peloterm.git
cd peloterm

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Running Tests

To run the test suite:

```bash
pytest
```

## References

- https://github.com/goldencheetah/goldencheetah
- https://github.com/joaovitoriasilva/endurain
- https://github.com/zacharyedwardbull/pycycling
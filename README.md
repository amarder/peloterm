# peloterm

A beautiful cycling metrics visualization tool that displays your real-time:

- Power ⚡
- Speed 🚴
- Cadence 🔄
- Heart Rate 💓

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
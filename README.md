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

## Installation

```bash
pip install git+https://github.com/amarder/peloterm.git
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

**Example workflow:**
1. Run `peloterm start`
2. See the list of devices it's waiting for
3. Turn on your heart rate monitor, cadence sensor, and trainer
4. Watch as each device connects in real-time
5. Start your workout once all devices are connected!

### Command Options

The `start` command supports these options:

- `--config PATH` - Use a specific configuration file
- `--timeout 60` - Set connection timeout in seconds (default: 60)
- `--debug` - Enable debug output
- `--web/--no-web` - Enable/disable web UI (default: enabled)
- `--port 8000` - Set web server port
- `--duration 30` - Set target ride duration in minutes

Examples:
```bash
# Use the default listening mode
peloterm start

# Listen for devices with 2-minute timeout
peloterm start --timeout 120

# Start without web UI
peloterm start --no-web

# Use debug mode to troubleshoot connections
peloterm start --debug
```

## Requirements

- Python 3.8 or higher
- Bluetooth LE capable hardware
- Compatible sensors (heart rate, cadence, power, speed)

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

## Roadmap

- [ ] Post to strava

## References

- https://github.com/goldencheetah/goldencheetah
- https://github.com/joaovitoriasilva/endurain
- https://github.com/zacharyedwardbull/pycycling
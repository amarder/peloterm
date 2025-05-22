# peloterm

A beautiful terminal-based cycling metrics visualization tool that displays your real-time:

- Power ⚡
- Speed 🚴
- Cadence 🔄
- Heart Rate 💓

## Features

- Real-time BLE sensor connection
- Beautiful terminal-based graphs
- Support for multiple sensor types
- Easy-to-use command line interface
- Automatic device reconnection if connection is lost

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

Once your sensors are configured, start monitoring your cycling metrics:

```bash
peloterm start
```

This will connect to your configured sensors and display real-time metrics in your terminal.

### Device Reconnection

If a device gets disconnected during your ride, peloterm will automatically attempt to reconnect:
- Up to 3 reconnection attempts will be made
- Each attempt is spaced 2 seconds apart
- The display will continue showing the last known values during reconnection
- Once reconnected, the metrics will automatically resume updating

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
- [ ] Think about UI

## References

- https://github.com/goldencheetah/goldencheetah
- https://github.com/joaovitoriasilva/endurain
- https://github.com/zacharyedwardbull/pycycling
# Peloterm

A beautiful terminal-based cycling metrics visualization tool that displays your real-time:
- Heart Rate 💓
- Cadence 🔄
- Power ⚡
- Speed 🚴

## Features

- Real-time BLE sensor connection
- Beautiful terminal-based graphs
- Support for multiple sensor types
- Easy-to-use command line interface

## Installation

```bash
pip install peloterm
```

## Usage

Start monitoring your cycling metrics:

```bash
peloterm start
```

View available sensors:

```bash
peloterm scan
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

## License

MIT License 
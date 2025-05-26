# Peloterm

A cycling metrics application that connects to Bluetooth sensors to display real-time performance data while you ride. Supports embedding compatible streaming content (like Jellyfin) in the built-in media player using HTML iframes. When you're done, easily save and upload your rides to Strava.

## Features

- Real-time BLE sensor connection (heart rate, power, cadence, speed)
- Modern web-based UI with configurable video integration
- Automatic ride recording with FIT file generation
- Interactive Strava upload
- Smart listening mode - turn on devices when you're ready

## Installation

```bash
pip install peloterm
```

## Quick Start

1. **First time setup - scan for your sensors:**
   ```bash
   peloterm scan
   ```
   This saves your device addresses to a config file, so you only need to do this once.

2. **Start your ride:**
   ```bash
   peloterm start
   ```

3. **Turn on your devices** when prompted and start cycling!

4. **Press Ctrl+C when done** to stop the session.

## Web Interface

When you run `peloterm start`, a web interface opens at http://localhost:8000 with:
- Real-time cycling metrics
- Interactive chart
- Configurable video panel (Jellyfin by default)

## Contributing

Want to contribute? Check out our [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, project structure, and how to submit pull requests.

# peloterm

A beautiful cycling metrics visualization tool that displays your real-time:

- Power ⚡
- Speed 🚴
- Cadence 🔄
- Heart Rate 💓

## Features

- Real-time BLE sensor connection
- Modern web-based UI with configurable video integration (YouTube by default)
- Support for multiple sensor types
- Easy-to-use command line interface
- Automatic device reconnection if connection is lost

## Configuration

peloterm uses a YAML configuration file to store your device settings and preferences. You can find an example configuration in `config.example.yaml`.

### Video Integration

The web UI includes a configurable iframe that can display any website. By default, it's set to YouTube, but you can change it to any website that allows embedding:

```yaml
# URL for the iframe in the web UI
iframe_url: "https://www.youtube.com"
```

Note: Some websites may block embedding through iframes due to security policies.

### Device Configuration

## Installation

```bash
pip install git+https://github.com/amarder/peloterm.git
```
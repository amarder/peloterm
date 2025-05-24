# PeloTerm Vue UI

A modern Vue 3 implementation of the PeloTerm web interface, replacing the original monolithic HTML/JavaScript with a component-based architecture.

## 🚀 Improvements Over Original

### Architecture Benefits
- **Component-based**: Modular, reusable components instead of a single 611-line HTML file
- **TypeScript**: Full type safety for better development experience and fewer runtime errors
- **Reactive State**: Vue's reactivity system for efficient UI updates
- **Modern Tooling**: Vite for fast development and optimized builds
- **Hot Module Replacement**: Instant updates during development

### Code Organization
```
src/
├── components/           # Reusable UI components
│   ├── VideoPanel.vue   # Video iframe with resize functionality
│   ├── MetricsPanel.vue # Container for metrics display
│   ├── TimeWidget.vue   # Time and progress display
│   └── MetricCard.vue   # Individual metric with chart
├── composables/         # Reusable logic
│   ├── useWebSocket.ts  # WebSocket connection management
│   └── useConfig.ts     # Configuration loading
├── types/               # TypeScript definitions
│   └── index.ts         # Shared interfaces
└── assets/              # Global styles
```

### Features Preserved
- ✅ Real-time WebSocket metrics updates
- ✅ Interactive Chart.js visualizations
- ✅ Resizable video panel
- ✅ Responsive mobile design
- ✅ Dark theme matching original
- ✅ Historical data processing
- ✅ All original functionality

### New Capabilities
- 🎯 **Better Error Handling**: Proper error boundaries and user feedback
- 🔧 **Easier Customization**: Component props for easy configuration
- 📱 **Enhanced Mobile**: Better responsive behavior
- 🎨 **Theme System**: Easier to add themes and customization
- 🧪 **Testable**: Components can be unit tested
- 📦 **Modular**: Easy to add new metrics or features

## 🛠 Development

### Prerequisites
- Node.js 18+ 
- Python 3.10+ (for FastAPI backend)

### Quick Start
```bash
# Install dependencies
npm install

# Development mode (with backend proxy)
npm run dev

# Or run both Vue and FastAPI together
python dev.py
```

### Build for Production
```bash
# Build and output to ../static for FastAPI to serve
npm run build
```

### Development URLs
- **Vue Dev Server**: http://localhost:5173 (with API proxy)
- **FastAPI Backend**: http://localhost:8000
- **API Config**: http://localhost:8000/api/config

## 🏗 Architecture

### Component Hierarchy
```
App.vue
├── VideoPanel.vue          # Video iframe + resize handle
└── MetricsPanel.vue        # Metrics container
    ├── TimeWidget.vue      # Clock + progress bar
    └── MetricCard.vue      # Individual metric + chart
```

### Data Flow
1. **App.vue** loads config and establishes WebSocket connection
2. **useWebSocket** composable manages real-time data
3. **MetricsPanel** distributes data to individual metric cards
4. **MetricCard** components update their charts reactively

### State Management
- **Reactive refs** for component-local state
- **Props/Events** for parent-child communication
- **Composables** for shared logic (WebSocket, config)
- **Pinia** available for complex state (future use)

## 🎨 Styling

- **Scoped CSS** in each component
- **CSS Custom Properties** for theming
- **Mobile-first** responsive design
- **Dark theme** matching original PeloTerm aesthetic

## 🔌 API Integration

The Vue app integrates seamlessly with the existing FastAPI backend:

- **Configuration**: `GET /api/config`
- **Real-time Data**: `WebSocket /ws`
- **Static Assets**: Served from `/static`

## 🚀 Future Enhancements

The Vue architecture makes these additions much easier:

- **Settings Panel**: Component for configuring iframe URLs, metrics
- **Multiple Themes**: Light/dark mode toggle
- **Custom Metrics**: User-defined metrics and charts
- **Data Export**: Download ride data as CSV/JSON
- **Workout Plans**: Integration with training programs
- **Social Features**: Share rides, compare metrics

## 📊 Performance

- **Smaller Bundle**: Tree-shaking removes unused code
- **Faster Updates**: Vue's reactivity is more efficient than manual DOM manipulation
- **Better Caching**: Vite optimizes asset loading
- **Code Splitting**: Lazy load components as needed

## 🧪 Testing

```bash
# Run unit tests
npm run test:unit

# Type checking
npm run type-check

# Linting
npm run lint
```

## 📝 Migration Notes

The Vue implementation maintains 100% API compatibility with the original:
- Same WebSocket protocol
- Same configuration format
- Same visual design
- Same responsive behavior

You can switch between implementations without changing the backend.

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Type-Check, Compile and Minify for Production

```sh
npm run build
```

### Run Unit Tests with [Vitest](https://vitest.dev/)

```sh
npm run test:unit
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```

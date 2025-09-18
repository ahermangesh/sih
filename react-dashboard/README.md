# Dolphin - Argo Float Dashboard

A modern React.js frontend for the Argo float data visualization and analysis system.

## Features

- 🤖 **AI Chatbot Integration**: Interactive Dolphin assistant for ocean data queries
- 🗺️ **Interactive Indian Ocean Map**: Visualize float locations with real-time data
- 📊 **Data Filtering**: Advanced filters for temperature, salinity, and depth
- 📈 **Real-time Charts**: Dynamic data visualization and statistics
- 🎨 **Modern UI**: Clean, responsive design with Material Design principles

## Project Structure

```
react-dashboard/
├── src/
│   ├── components/
│   │   ├── Dashboard/          # Main dashboard layout
│   │   ├── Sidebar/           # AI chatbot sidebar
│   │   ├── Map/               # Indian ocean map view
│   │   └── RightPanel/        # Filters and charts panel
│   ├── App.tsx               # Main application component
│   └── index.tsx             # Application entry point
├── public/                   # Static assets
└── package.json             # Dependencies and scripts
```

## Installation

1. Navigate to the frontend directory:
   ```bash
   cd react-dashboard
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

4. Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

## Environment Configuration

Create a `.env` file in the root directory:

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WEBSOCKET_URL=ws://localhost:8000/ws
```

## Backend Integration

The frontend is designed to integrate seamlessly with the Python backend via:

- **REST API calls** for data fetching and filtering
- **WebSocket connections** for real-time updates
- **Environment variables** for configuring backend endpoints

### API Endpoints Expected

- `GET /api/floats` - Fetch all float data
- `POST /api/floats/filter` - Apply filters to float data
- `POST /api/chat` - Send messages to AI chatbot
- `GET /api/stats` - Fetch dashboard statistics
- `WebSocket /ws` - Real-time data updates

## Development

### Available Scripts

- `npm start` - Runs the app in development mode
- `npm run build` - Builds the app for production
- `npm test` - Launches the test runner
- `npm run eject` - Ejects from Create React App (one-way operation)

### Code Style

- TypeScript for type safety
- CSS modules for component styling
- ESLint for code quality
- Prettier for code formatting

## Deployment

1. Build the production version:
   ```bash
   npm run build
   ```

2. The `build` folder contains the optimized production build ready for deployment.

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Create feature branches from `main`
2. Follow TypeScript and React best practices
3. Ensure responsive design across all screen sizes
4. Test thoroughly before creating pull requests

## Technologies Used

- **React 18** - Frontend framework
- **TypeScript** - Type safety
- **CSS3** - Styling with modern features
- **SVG** - Map and chart graphics
- **WebSocket** - Real-time communication
- **Axios** - HTTP client (when backend is ready)

## Future Enhancements

- [ ] Leaflet.js integration for advanced mapping
- [ ] Chart.js for enhanced data visualization
- [ ] PWA support for mobile devices
- [ ] Dark/Light theme toggle
- [ ] Multi-language support
- [ ] Export functionality for charts and data

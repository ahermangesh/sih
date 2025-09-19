# FloatChat Dashboard

A modern Next.js 14 dashboard for exploring ARGO ocean data with AI-powered chat interface.

## 🌊 Features

- **Interactive Map**: Leaflet-based map with ARGO float markers and clustering
- **AI Chat Interface**: Real-time chat with FloatChat AI for ocean data queries
- **Scientific Visualizations**: Plotly-based charts for temperature, salinity, and depth profiles
- **Real-time Dashboard**: Live statistics and activity monitoring
- **3D Globe View**: Cesium integration for 3D ocean exploration
- **Responsive Design**: Mobile-friendly with dark/light theme support

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm 8+
- Python backend running on `localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

## 🏗️ Architecture

```
src/
├── app/                    # Next.js 14 App Router
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Main dashboard page
│   ├── globals.css        # Global styles and Tailwind
│   └── providers.tsx      # React Query provider
├── components/            # React components
│   ├── InteractiveMap.tsx # Leaflet map with float markers
│   ├── ChatPanel.tsx      # AI chat interface
│   └── DashboardPanel.tsx # Statistics and charts
├── lib/                   # Utilities and services
│   ├── api.ts            # API service for backend
│   └── utils.ts          # Helper functions
└── types/                 # TypeScript definitions
    └── index.ts          # Shared type definitions
```

## 🛠️ Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom ocean theme
- **Maps**: Leaflet + React Leaflet with clustering
- **Charts**: Plotly.js for scientific visualizations
- **3D Globe**: Cesium (optional)
- **Animations**: Framer Motion
- **State Management**: Zustand + React Query
- **Backend Integration**: Axios with React Query

## 🗺️ Map Features

- **ARGO Float Markers**: Color-coded by status (active, delayed, inactive)
- **Clustering**: Automatic marker clustering for better performance
- **Interactive Popups**: Float details with quick actions
- **Layer Controls**: Toggle different data layers
- **3D Globe**: Optional Cesium integration
- **Real-time Updates**: WebSocket integration for live data

## 💬 Chat Features

- **AI Assistant**: Natural language queries about ocean data
- **Context Awareness**: Maintains conversation context
- **Quick Actions**: Pre-defined query buttons
- **Voice Support**: Speech-to-text integration (planned)
- **Multilingual**: Support for multiple languages
- **Data Integration**: Real-time ARGO data queries

## 📊 Dashboard Features

- **Key Metrics**: Total floats, active floats, profiles
- **Ocean Distribution**: Float distribution by ocean/country
- **Scientific Charts**: Temperature and salinity profiles
- **Activity Feed**: Recent system activity and updates
- **Real-time Stats**: Live updating statistics
- **Export Options**: Data export in JSON/CSV formats

## 🔧 Configuration

### Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=your_token_here
NEXT_PUBLIC_CESIUM_ACCESS_TOKEN=your_token_here
```

### Backend Integration

The dashboard connects to the FloatChat Python backend:

- **Chat API**: `/api/v1/real-chat/query`
- **Float Data**: `/api/v1/floats`
- **Dashboard Stats**: `/api/v1/dashboard/stats`
- **WebSocket**: `/api/v1/ws`

## 🎨 Theming

Ocean-inspired color palette:

- **Ocean Blue**: Primary brand color
- **Deep Sea**: Dark theme colors
- **Coral**: Accent colors for alerts
- **Glass Effect**: Backdrop blur effects
- **Animations**: Smooth micro-interactions

## 📱 Responsive Design

- **Desktop**: Full layout with map, chat, and dashboard
- **Tablet**: Collapsible panels with tab navigation
- **Mobile**: Stacked layout with bottom navigation
- **Touch**: Optimized for touch interactions

## 🔄 Real-time Features

- **WebSocket Connection**: Live data updates
- **Auto-refresh**: Periodic data synchronization
- **Offline Support**: Graceful degradation
- **Error Recovery**: Automatic reconnection

## 🧪 Development

### Scripts

```bash
npm run dev          # Development server
npm run build        # Production build
npm run start        # Production server
npm run lint         # ESLint checking
npm run type-check   # TypeScript checking
```

### Adding New Components

1. Create component in `src/components/`
2. Add TypeScript interfaces in `src/types/`
3. Import and use in pages
4. Update API service if needed

## 🚀 Deployment

### Build for Production

```bash
npm run build
npm run start
```

### Environment Setup

- Set production API URLs
- Configure CDN for static assets
- Enable performance monitoring
- Set up error tracking

## 📚 API Integration

The dashboard integrates with the FloatChat Python backend for:

- **Ocean Data Queries**: Real ARGO float data
- **AI Chat**: Natural language processing
- **Real-time Updates**: WebSocket connections
- **Authentication**: JWT token management
- **Error Handling**: Graceful error recovery

## 🌟 Future Enhancements

- **Voice Interface**: Speech-to-text/text-to-speech
- **3D Visualization**: Enhanced Cesium integration
- **Machine Learning**: Predictive ocean modeling
- **Collaboration**: Multi-user features
- **Mobile App**: React Native version
- **AR/VR**: Immersive ocean exploration

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## 📄 License

MIT License - see LICENSE file for details.

---

Built with ❤️ for oceanographic research and marine science education.
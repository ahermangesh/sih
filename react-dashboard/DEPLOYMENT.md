# Deployment Guide - Dolphin Dashboard

## Local Development Setup

1. **Prerequisites**
   - Node.js 16+ installed
   - npm or yarn package manager

2. **Environment Setup**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env file with your backend URLs
   REACT_APP_API_URL=http://localhost:8000
   REACT_APP_WEBSOCKET_URL=ws://localhost:8000/ws
   ```

3. **Install & Run**
   ```bash
   # Install dependencies
   npm install
   
   # Start development server
   npm start
   ```

## Backend Integration Checklist

When your Python backend is ready, follow these steps:

### 1. Update API Service
- [ ] Uncomment actual API calls in `src/services/apiService.ts`
- [ ] Remove mock data methods
- [ ] Test all endpoints

### 2. Required Backend Endpoints

The frontend expects these endpoints from your backend:

```
GET  /api/floats           - Get all float data
POST /api/floats/filter    - Filter floats by criteria
POST /api/chat             - Send message to AI chatbot
GET  /api/stats            - Get dashboard statistics
WS   /ws                   - WebSocket for real-time updates
```

### 3. API Response Formats

**Float Data Response:**
```json
{
  "floats": [
    {
      "id": "F001",
      "lat": 19.0760,
      "lng": 72.8777,
      "temperature": 28.5,
      "salinity": 35.2,
      "depth": 100,
      "status": "active",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Chat Response:**
```json
{
  "id": "msg_123",
  "response": "AI response text",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Stats Response:**
```json
{
  "totalFloats": 627,
  "activeFloats": 442,
  "dataPoints": 15847,
  "maxTemperature": 31.2,
  "avgSalinity": 35.1
}
```

### 4. CORS Configuration

Ensure your Python backend allows CORS from the frontend:

```python
# For FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. WebSocket Integration

The frontend connects to WebSocket for real-time updates:

```python
# Expected WebSocket message format
{
    "type": "float_update",
    "data": {
        "id": "F001",
        "temperature": 28.7,
        "timestamp": "2024-01-15T10:35:00Z"
    }
}
```

## Production Deployment

### 1. Build for Production
```bash
npm run build
```

### 2. Deploy Options

**Option A: Static Hosting (Netlify, Vercel)**
- Upload the `build` folder
- Configure environment variables
- Set up redirects for SPA routing

**Option B: Docker Deployment**
```dockerfile
FROM nginx:alpine
COPY build/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Option C: Same Server as Backend**
- Copy `build` folder to your Python app's static directory
- Serve from your Python backend

### 3. Environment Variables for Production
```env
REACT_APP_API_URL=https://your-backend-domain.com
REACT_APP_WEBSOCKET_URL=wss://your-backend-domain.com/ws
REACT_APP_DEBUG=false
```

## Testing the Integration

1. **Start Backend Server**
   ```bash
   cd ../  # Go to main project directory
   python -m uvicorn app.main:app --reload
   ```

2. **Start Frontend**
   ```bash
   cd react-dashboard
   npm start
   ```

3. **Verify Integration**
   - [ ] Map loads with float data
   - [ ] Filters work correctly
   - [ ] Chat responds to messages
   - [ ] Real-time updates via WebSocket
   - [ ] Statistics display correctly

## Troubleshooting

**Common Issues:**

1. **CORS Errors**
   - Ensure backend CORS configuration includes frontend URL
   - Check browser console for specific CORS messages

2. **API Connection Failed**
   - Verify backend server is running
   - Check API URLs in environment variables
   - Inspect network tab for failed requests

3. **WebSocket Connection Failed**
   - Ensure WebSocket endpoint is correct
   - Check if backend supports WebSocket connections
   - Verify no proxy/firewall blocking WebSocket

4. **Map Not Loading**
   - Check browser console for JavaScript errors
   - Verify all dependencies installed correctly
   - Test with mock data first

## Performance Optimization

1. **Bundle Analysis**
   ```bash
   npm run build
   npx webpack-bundle-analyzer build/static/js/*.js
   ```

2. **Optimize Images**
   - Use WebP format for images
   - Implement lazy loading
   - Add proper caching headers

3. **Code Splitting**
   - Implement React.lazy() for route-based splitting
   - Use dynamic imports for heavy components

## Security Considerations

1. **Environment Variables**
   - Never commit `.env` files to git
   - Use different configs for dev/staging/prod
   - Rotate API keys regularly

2. **API Security**
   - Implement proper authentication
   - Use HTTPS in production
   - Validate all user inputs

3. **Content Security Policy**
   - Add CSP headers for XSS protection
   - Whitelist only necessary domains
   - Monitor for violations

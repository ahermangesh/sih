// API service for backend integration
// This file contains all API calls that will connect to your Python backend

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface FloatData {
  id: string;
  lat: number;
  lng: number;
  temperature: number;
  salinity: number;
  depth: number;
  status: 'active' | 'inactive';
  timestamp: string;
}

export interface ChatMessage {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

export interface FilterParams {
  temperature?: { min: number; max: number };
  salinity?: { min: number; max: number };
  depth?: { min: number; max: number };
  status?: 'active' | 'inactive' | 'all';
}

export interface DashboardStats {
  totalFloats: number;
  activeFloats: number;
  dataPoints: number;
  maxTemperature: number;
  avgSalinity: number;
}

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  // Float data endpoints
  async getFloats(): Promise<FloatData[]> {
    try {
      // When backend is ready, uncomment this:
      // const response = await fetch(`${this.baseUrl}/api/floats`);
      // return await response.json();
      
      // Mock data for now
      return this.getMockFloats();
    } catch (error) {
      console.error('Error fetching floats:', error);
      return this.getMockFloats();
    }
  }

  async getFilteredFloats(filters: FilterParams): Promise<FloatData[]> {
    try {
      // When backend is ready, uncomment this:
      // const response = await fetch(`${this.baseUrl}/api/floats/filter`, {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify(filters),
      // });
      // return await response.json();
      
      // Mock filtered data for now
      const allFloats = this.getMockFloats();
      return allFloats.filter(float => {
        const tempMatch = !filters.temperature || 
          (float.temperature >= filters.temperature.min && float.temperature <= filters.temperature.max);
        const salinityMatch = !filters.salinity || 
          (float.salinity >= filters.salinity.min && float.salinity <= filters.salinity.max);
        const depthMatch = !filters.depth || 
          (float.depth >= filters.depth.min && float.depth <= filters.depth.max);
        const statusMatch = !filters.status || filters.status === 'all' || float.status === filters.status;
        
        return tempMatch && salinityMatch && depthMatch && statusMatch;
      });
    } catch (error) {
      console.error('Error filtering floats:', error);
      return this.getMockFloats();
    }
  }

  // Chat endpoints
  async sendChatMessage(message: string): Promise<ChatMessage> {
    try {
      // When backend is ready, uncomment this:
      // const response = await fetch(`${this.baseUrl}/api/chat`, {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify({ message }),
      // });
      // const data = await response.json();
      // return {
      //   id: data.id,
      //   text: data.response,
      //   isUser: false,
      //   timestamp: new Date(data.timestamp),
      // };
      
      // Mock AI response for now
      return {
        id: Date.now().toString(),
        text: this.getMockAIResponse(message),
        isUser: false,
        timestamp: new Date(),
      };
    } catch (error) {
      console.error('Error sending chat message:', error);
      return {
        id: Date.now().toString(),
        text: 'Sorry, I encountered an error. Please try again.',
        isUser: false,
        timestamp: new Date(),
      };
    }
  }

  // Dashboard stats
  async getDashboardStats(): Promise<DashboardStats> {
    try {
      // When backend is ready, uncomment this:
      // const response = await fetch(`${this.baseUrl}/api/stats`);
      // return await response.json();
      
      // Mock stats for now
      return {
        totalFloats: 627,
        activeFloats: 442,
        dataPoints: 15847,
        maxTemperature: 31.2,
        avgSalinity: 35.1,
      };
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      return {
        totalFloats: 0,
        activeFloats: 0,
        dataPoints: 0,
        maxTemperature: 0,
        avgSalinity: 0,
      };
    }
  }

  // Mock data methods (remove when backend is ready)
  private getMockFloats(): FloatData[] {
    return [
      { id: 'F001', lat: 19.0760, lng: 72.8777, temperature: 28.5, salinity: 35.2, depth: 100, status: 'active', timestamp: '2024-01-15T10:30:00Z' },
      { id: 'F002', lat: 13.0827, lng: 80.2707, temperature: 29.1, salinity: 35.8, depth: 150, status: 'active', timestamp: '2024-01-15T10:30:00Z' },
      { id: 'F003', lat: 22.5726, lng: 88.3639, temperature: 27.8, salinity: 34.9, depth: 200, status: 'inactive', timestamp: '2024-01-15T10:30:00Z' },
      { id: 'F004', lat: 12.9716, lng: 77.5946, temperature: 26.3, salinity: 35.1, depth: 180, status: 'active', timestamp: '2024-01-15T10:30:00Z' },
      { id: 'F005', lat: 15.2993, lng: 74.1240, temperature: 28.9, salinity: 35.5, depth: 120, status: 'active', timestamp: '2024-01-15T10:30:00Z' },
      { id: 'F006', lat: 11.0168, lng: 76.9558, temperature: 30.2, salinity: 36.1, depth: 90, status: 'active', timestamp: '2024-01-15T10:30:00Z' },
    ];
  }

  private getMockAIResponse(message: string): string {
    const responses = [
      'Based on the current data, I can see interesting patterns in ocean temperatures around the Indian coast.',
      'The salinity levels you\'re asking about show seasonal variations. Let me analyze the latest float data.',
      'That\'s a great question about ocean currents. The Argo float data indicates...',
      'I notice you\'re interested in temperature trends. The current readings show...',
      'The depth measurements from our floats suggest...',
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  }
}

// WebSocket service for real-time updates
export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;

  constructor() {
    this.url = process.env.REACT_APP_WEBSOCKET_URL || 'ws://localhost:8000/ws';
  }

  connect(onMessage: (data: any) => void): void {
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
      };
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        onMessage(data);
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => this.connect(onMessage), 5000);
      };
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}

export default new ApiService();

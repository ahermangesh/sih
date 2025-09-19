// Types for FloatChat Dashboard

export interface FloatData {
  id: string;
  platform_id: string;
  latitude: number;
  longitude: number;
  last_position_date: string;
  status: 'active' | 'inactive' | 'delayed' | 'stopped';
  country: string;
  ocean: string;
  profiles_count: number;
  latest_profile?: ProfileData;
}

export interface ProfileData {
  id: string;
  float_id: string;
  cycle_number: number;
  direction: 'ascending' | 'descending';
  date: string;
  latitude: number;
  longitude: number;
  measurements_count: number;
  temperature_range?: [number, number];
  salinity_range?: [number, number];
  pressure_range?: [number, number];
}

export interface MeasurementData {
  id: string;
  profile_id: string;
  pressure: number;
  temperature: number;
  salinity: number;
  depth: number;
  quality_flag: string;
  measurement_date: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  loading?: boolean;
  metadata?: {
    query_type?: string;
    confidence?: number;
    data_sources?: string[];
    processing_time?: number;
    error?: boolean;
    [key: string]: any;
  };
}

export interface DashboardStats {
  total_floats: number;
  active_floats: number;
  total_profiles: number;
  latest_data_date: string;
  coverage_stats: {
    oceans: Record<string, number>;
    countries: Record<string, number>;
  };
  recent_activity: ActivityItem[];
}

export interface ActivityItem {
  id: string;
  type: 'new_float' | 'new_profile' | 'data_update' | 'system_event';
  title: string;
  description: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface MapConfig {
  center: [number, number];
  zoom: number;
  minZoom: number;
  maxZoom: number;
  clustering: boolean;
  show3D: boolean;
  layerControls: boolean;
}

export interface FilterParams {
  dateRange?: {
    start: Date;
    end: Date;
  };
  temperatureRange?: [number, number];
  salinityRange?: [number, number];
  depthRange?: [number, number];
  status?: string[];
  oceans?: string[];
  countries?: string[];
  boundingBox?: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
}

export interface PlotConfig {
  type: 'temperature_profile' | 'salinity_profile' | 'depth_time' | 'trajectory' | 'scatter';
  title: string;
  data: any[];
  layout?: any;
  config?: any;
}

export interface APIResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface WebSocketMessage {
  type: 'float_update' | 'new_profile' | 'chat_response' | 'system_status';
  payload: any;
  timestamp: string;
}
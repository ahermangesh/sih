'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'

// Types for dashboard context
export interface DashboardFilter {
  region?: string
  ocean?: string
  status?: string[]
  timeRange?: {
    start?: string
    end?: string
  }
  searchQuery?: string
  coordinates?: {
    lat: number
    lng: number
    radius?: number
  }
}

export interface DashboardData {
  totalFloats: number
  activeFloats: number
  inactiveFloats: number
  delayedFloats: number
  region: string
  lastUpdated: string
  oceanStats?: {
    [ocean: string]: number
  }
  recentActivity?: Array<{
    id: string
    type: string
    message: string
    timestamp: string
  }>
  floatDetails?: Array<{
    id: string
    wmo_id: string
    latitude: number
    longitude: number
    status: string
    platform_type: string
    program: string
    country: string
    last_position_date: string
  }>
}

interface DashboardContextType {
  filter: DashboardFilter
  data: DashboardData | null
  loading: boolean
  error: string | null
  updateFilter: (newFilter: Partial<DashboardFilter>) => void
  refreshData: () => Promise<void>
  setFromChatQuery: (query: string) => void
}

const defaultFilter: DashboardFilter = {
  region: 'Indian Ocean',
  ocean: 'Indian',
  status: ['active', 'inactive', 'delayed'],
  searchQuery: 'Indian Ocean ARGO floats'
}

const defaultData: DashboardData = {
  totalFloats: 0,
  activeFloats: 0,
  inactiveFloats: 0,
  delayedFloats: 0,
  region: 'Indian Ocean',
  lastUpdated: new Date().toISOString()
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined)

export const useDashboard = () => {
  const context = useContext(DashboardContext)
  if (!context) {
    throw new Error('useDashboard must be used within a DashboardProvider')
  }
  return context
}

// Extract location/region info from chat queries
const extractRegionFromQuery = (query: string): Partial<DashboardFilter> => {
  const lowerQuery = query.toLowerCase()
  
  // Ocean detection
  if (lowerQuery.includes('indian ocean')) {
    return { region: 'Indian Ocean', ocean: 'Indian' }
  }
  if (lowerQuery.includes('pacific ocean')) {
    return { region: 'Pacific Ocean', ocean: 'Pacific' }
  }
  if (lowerQuery.includes('atlantic ocean')) {
    return { region: 'Atlantic Ocean', ocean: 'Atlantic' }
  }
  if (lowerQuery.includes('arctic ocean')) {
    return { region: 'Arctic Ocean', ocean: 'Arctic' }
  }
  if (lowerQuery.includes('southern ocean') || lowerQuery.includes('antarctic ocean')) {
    return { region: 'Southern Ocean', ocean: 'Southern' }
  }
  
  // Specific regions
  if (lowerQuery.includes('bay of bengal')) {
    return { region: 'Bay of Bengal', ocean: 'Indian' }
  }
  if (lowerQuery.includes('arabian sea')) {
    return { region: 'Arabian Sea', ocean: 'Indian' }
  }
  
  // Status detection
  const statusFilters: string[] = []
  if (lowerQuery.includes('active')) statusFilters.push('active')
  if (lowerQuery.includes('inactive')) statusFilters.push('inactive')
  if (lowerQuery.includes('delayed')) statusFilters.push('delayed')
  
  return {
    status: statusFilters.length > 0 ? statusFilters : ['active', 'inactive', 'delayed']
  }
}

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [filter, setFilter] = useState<DashboardFilter>(defaultFilter)
  const [data, setData] = useState<DashboardData | null>(defaultData)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Helper function to determine ocean from coordinates
  const getOceanFromCoordinates = (lat: number, lng: number): string => {
    // Indian Ocean coordinates
    if (lat >= -50 && lat <= 30 && lng >= 20 && lng <= 150) {
      return 'Indian Ocean'
    }
    // Pacific Ocean coordinates  
    if (lng >= 120 || lng <= -60) {
      return 'Pacific Ocean'
    }
    // Atlantic Ocean coordinates
    if (lng >= -80 && lng <= 20) {
      return 'Atlantic Ocean'
    }
    // Arctic Ocean
    if (lat >= 66) {
      return 'Arctic Ocean'
    }
    // Southern Ocean
    if (lat <= -60) {
      return 'Southern Ocean'
    }
    
    return 'Other'
  }

  // Fetch dashboard data based on current filter
  const fetchDashboardData = async (currentFilter: DashboardFilter): Promise<DashboardData> => {
    try {
      console.log('Fetching dashboard data for filter:', currentFilter)
      
      // Fetch stats from backend
      const statsResponse = await fetch('http://localhost:8002/api/v1/dashboard/stats')
      if (!statsResponse.ok) {
        throw new Error('Failed to fetch dashboard stats')
      }
      const stats = await statsResponse.json()
      console.log('Backend stats:', stats)
      
      // Fetch floats data for filtering
      const floatsResponse = await fetch('http://localhost:8002/api/v1/dashboard/floats/locations')
      if (!floatsResponse.ok) {
        throw new Error('Failed to fetch floats data')
      }
      const floats = await floatsResponse.json()
      console.log('Floats data received:', floats.length, 'floats')
      
      // Add ocean information to each float based on coordinates
      const floatsWithOcean = floats.map((f: any) => ({
        ...f,
        ocean: getOceanFromCoordinates(f.latitude, f.longitude)
      }))
      
      // Filter floats based on current filter
      let filteredFloats = floatsWithOcean
      
      if (currentFilter.ocean) {
        filteredFloats = filteredFloats.filter((f: any) => 
          f.ocean && f.ocean.toLowerCase().includes(currentFilter.ocean!.toLowerCase())
        )
      }
      
      if (currentFilter.region) {
        filteredFloats = filteredFloats.filter((f: any) => 
          f.ocean && f.ocean.toLowerCase().includes(currentFilter.region!.toLowerCase())
        )
      }
      
      if (currentFilter.status && currentFilter.status.length > 0) {
        filteredFloats = filteredFloats.filter((f: any) => 
          currentFilter.status!.includes(f.status)
        )
      }
      
      // Calculate filtered stats with proper status mapping
      const totalFloats = filteredFloats.length
      const activeFloats = filteredFloats.filter((f: any) => f.status === 'active').length
      const inactiveFloats = filteredFloats.filter((f: any) => f.status === 'inactive').length
      const delayedFloats = filteredFloats.filter((f: any) => 
        f.status === 'delayed' || f.status === 'recent' || f.status === 'bgc'
      ).length
      
      console.log('Filtered results:', {
        total: totalFloats,
        active: activeFloats,
        inactive: inactiveFloats,
        delayed: delayedFloats,
        filter: currentFilter
      })
      
      // Ocean distribution
      const oceanStats: { [key: string]: number } = {}
      filteredFloats.forEach((f: any) => {
        if (f.ocean) {
          oceanStats[f.ocean] = (oceanStats[f.ocean] || 0) + 1
        }
      })
      
      return {
        totalFloats,
        activeFloats,
        inactiveFloats,
        delayedFloats,
        region: currentFilter.region || 'Global',
        lastUpdated: new Date().toISOString(),
        oceanStats,
        recentActivity: [
          {
            id: '1',
            type: 'search',
            message: `Filtered data for ${currentFilter.region || 'Global'} region`,
            timestamp: new Date().toISOString()
          }
        ],
        floatDetails: filteredFloats.map((f: any) => ({
          id: f.float_id || f.id,
          wmo_id: f.wmo_id,
          latitude: f.latitude,
          longitude: f.longitude,
          status: f.status,
          platform_type: f.platform_type || 'UNKNOWN',
          program: f.metadata?.program || 'UNKNOWN',
          country: f.metadata?.country || 'UNKNOWN',
          last_position_date: f.last_position_date || f.lastUpdate || new Date().toISOString()
        }))
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err)
      throw err
    }
  }

  const refreshData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const newData = await fetchDashboardData(filter)
      setData(newData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  const updateFilter = (newFilter: Partial<DashboardFilter>) => {
    const updatedFilter = { ...filter, ...newFilter }
    setFilter(updatedFilter)
  }

  const setFromChatQuery = (query: string) => {
    console.log('Chat query received:', query)
    const extractedFilter = extractRegionFromQuery(query)
    console.log('Extracted filter from query:', extractedFilter)
    const updatedFilter = { 
      ...filter, 
      ...extractedFilter,
      searchQuery: query 
    }
    console.log('Updated filter:', updatedFilter)
    setFilter(updatedFilter)
  }

  // Refresh data when filter changes
  useEffect(() => {
    refreshData()
  }, [filter])

  // Initial data load
  useEffect(() => {
    refreshData()
  }, [])

  const value: DashboardContextType = {
    filter,
    data,
    loading,
    error,
    updateFilter,
    refreshData,
    setFromChatQuery
  }

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  )
}
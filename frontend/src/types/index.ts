export interface MetricConfig {
  name: string
  key: string
  symbol: string
  color: string
}

export interface Config {
  iframe_url: string
  ride_duration_minutes: number
  ride_start_time: number
  iframe_options: Record<string, string>
  metrics: MetricConfig[]
}

export interface MetricsData {
  power?: number
  speed?: number
  cadence?: number
  heart_rate?: number
  timestamp?: number
  [key: string]: number | undefined
}

export interface ChartRange {
  min: number
  max: number
}

export interface ChartRanges {
  power: ChartRange
  speed: ChartRange
  cadence: ChartRange
  heart_rate: ChartRange
  [key: string]: ChartRange
} 
import type { Feature, Geometry, GeoJsonProperties } from 'geojson';

export type UserRole = 'ADMIN' | 'ANALYST' | 'VIEWER';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SystemStatus {
  status: string;
  service: string;
  version: string;
  environment: string;
  database_connected: boolean;
  ml_device: string;
  active_spills_count: number;
  active_investigations_count: number;
  total_vessels_tracked: number;
}

export type SpillStatus = 
  | 'NOT ANALYZED'
  | 'ANALYZING'
  | 'DETECTED'
  | 'NO SPILL'
  | 'REVIEW REQUIRED'
  | 'ACCEPTED'
  | 'REJECTED';

export interface SatelliteImage {
  id: number;
  product_id: string;
  satellite: string;
  sensor: string;
  acquisition_time: string;
  polarization: string;
  orbit: string;
  file_path: string;
  thumbnail_path?: string;
  metadata_json?: Record<string, any>;
  bounding_geometry?: any;
  created_at: string;
}

export interface SpillEvent {
  id: number;
  satellite_image_id?: number;
  detected_at: string;
  confidence: number;
  area_km2: number;
  perimeter_km: number;
  centroid?: { type: 'Point'; coordinates: [number, number] };
  bounding_box?: any;
  spill_geometry: any;
  status: SpillStatus;
  model_version: string;
  created_at: string;
  updated_at: string;
  satellite_image?: SatelliteImage;
}

export interface EnvironmentalData {
  id: number;
  timestamp: string;
  source: string;
  wind_speed: number;
  wind_direction: number;
  current_u: number;
  current_v: number;
  wave_height?: number;
  temperature?: number;
  geometry?: any;
  metadata_json?: Record<string, any>;
}

export type SimulationType = 'FORWARD' | 'BACKWARD';
export type SimulationStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface DriftParticle {
  id: number;
  simulation_id: number;
  particle_id: number;
  timestamp: string;
  position: { type: 'Point'; coordinates: [number, number] };
}

export interface DriftSimulation {
  id: number;
  spill_event_id: number;
  simulation_type: SimulationType;
  start_time: string;
  end_time: string;
  duration_hours: number;
  particle_count: number;
  model_name: string;
  parameters_json?: Record<string, any>;
  confidence: number;
  status: SimulationStatus;
  output_path?: string;
  origin_probability_geometry?: any;
  created_at: string;
  particles?: DriftParticle[];
}

export interface AisPosition {
  id: number;
  vessel_id: number;
  timestamp: string;
  position: { type: 'Point'; coordinates: [number, number] };
  speed?: number;
  course?: number;
  heading?: number;
  navigation_status?: string;
}

export interface Vessel {
  id: number;
  mmsi: string;
  imo?: string;
  name: string;
  ship_type: string;
  flag?: string;
  length?: number;
  width?: number;
  metadata_json?: Record<string, any>;
  positions?: AisPosition[];
}

export type PriorityLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface CandidateEvidenceItem {
  key: string;
  label: string;
  passed: boolean;
  score: number;
  detail: string;
}

export interface CandidateEvidence {
  spatial_distance_km: number;
  temporal_delta_hours: number;
  trajectory_heading_match_deg: number;
  speed_knots: number;
  anomalous_behavior_flag: boolean;
  ais_gap_detected: boolean;
  explanation_points: string[];
  evidence_breakdown: CandidateEvidenceItem[];
}

export interface VesselCandidate {
  id: number;
  spill_event_id: number;
  vessel_id: number;
  spatial_score: number;
  temporal_score: number;
  trajectory_score: number;
  behaviour_score: number;
  data_quality_score: number;
  overall_score: number;
  priority: PriorityLevel;
  explanation_json: CandidateEvidence;
  created_at: string;
  vessel?: Vessel;
}

export type InvestigationStatus = 
  | 'NEW'
  | 'UNDER REVIEW'
  | 'HIGH PRIORITY'
  | 'RESOLVED'
  | 'CLOSED';

export interface Investigation {
  id: number;
  spill_event_id: number;
  assigned_to?: number;
  status: InvestigationStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
  assignee?: User;
  spill_event?: SpillEvent;
}

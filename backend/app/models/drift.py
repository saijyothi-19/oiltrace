import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.spatial import GeoJSONGeometry

class SimulationType(str, enum.Enum):
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"

class SimulationStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DriftSimulation(Base):
    __tablename__ = "drift_simulations"

    id = Column(Integer, primary_key=True, index=True)
    spill_event_id = Column(Integer, ForeignKey("spill_events.id", ondelete="CASCADE"), nullable=False)
    simulation_type = Column(Enum(SimulationType), default=SimulationType.BACKWARD, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_hours = Column(Float, default=12.0, nullable=False)
    particle_count = Column(Integer, default=150, nullable=False)
    model_name = Column(String(100), default="Lagrangian-Eulerian OpenDrift Emulator", nullable=False)
    parameters_json = Column(JSON, nullable=True)
    confidence = Column(Float, default=0.85, nullable=False)
    status = Column(Enum(SimulationStatus), default=SimulationStatus.COMPLETED, nullable=False)
    output_path = Column(String(500), nullable=True)
    origin_probability_geometry = Column(GeoJSONGeometry, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    spill_event = relationship("SpillEvent", back_populates="drift_simulations")
    particles = relationship("DriftParticle", back_populates="simulation", cascade="all, delete-orphan")


class DriftParticle(Base):
    __tablename__ = "drift_particles"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("drift_simulations.id", ondelete="CASCADE"), nullable=False)
    particle_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    position = Column(GeoJSONGeometry, nullable=False)

    simulation = relationship("DriftSimulation", back_populates="particles")

from sqlalchemy import String, Float, Integer, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.database.session import Base

class Run(Base):
    __tablename__="simulation_history"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    created_at: Mapped[datetime]=mapped_column(DateTime)
    scenario: Mapped[str]=mapped_column(String(40))
    config: Mapped[dict]=mapped_column(JSON)
    summary: Mapped[dict]=mapped_column(JSON)
    schedule: Mapped[list]=mapped_column(JSON)

class GenerationRecord(Base):
    __tablename__="renewable_generation"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    solar_kw: Mapped[float]=mapped_column(Float)
    wind_kw: Mapped[float]=mapped_column(Float)
    solar_predicted_kw: Mapped[float]=mapped_column(Float,default=0)
    wind_predicted_kw: Mapped[float]=mapped_column(Float,default=0)
    source: Mapped[str]=mapped_column(String(30),default="synthetic")
    run_id: Mapped[str]=mapped_column(String(36),ForeignKey("simulation_history.id"),nullable=True,index=True)

class ConsumptionRecord(Base):
    __tablename__="electricity_consumption"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    residential_kw: Mapped[float]=mapped_column(Float)
    commercial_kw: Mapped[float]=mapped_column(Float)
    industrial_kw: Mapped[float]=mapped_column(Float)
    total_kw: Mapped[float]=mapped_column(Float)
    predicted_kw: Mapped[float]=mapped_column(Float,default=0)
    run_id: Mapped[str]=mapped_column(String(36),nullable=True,index=True)

class WeatherRecord(Base):
    __tablename__="weather"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    irradiance: Mapped[float]=mapped_column(Float)
    temperature: Mapped[float]=mapped_column(Float)
    humidity: Mapped[float]=mapped_column(Float)
    cloud_cover: Mapped[float]=mapped_column(Float)
    wind_speed: Mapped[float]=mapped_column(Float)
    wind_direction: Mapped[float]=mapped_column(Float)
    air_density: Mapped[float]=mapped_column(Float)
    run_id: Mapped[str]=mapped_column(String(36),nullable=True,index=True)

class PowerMeasurement(Base):
    __tablename__="power_measurements"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    voltage: Mapped[float]=mapped_column(Float)
    current: Mapped[float]=mapped_column(Float)
    frequency: Mapped[float]=mapped_column(Float)
    active_power: Mapped[float]=mapped_column(Float)
    reactive_power: Mapped[float]=mapped_column(Float)
    apparent_power: Mapped[float]=mapped_column(Float)
    power_factor: Mapped[float]=mapped_column(Float)
    transformer_loading: Mapped[float]=mapped_column(Float)
    run_id: Mapped[str]=mapped_column(String(36),nullable=True,index=True)

class BatteryStatus(Base):
    __tablename__="battery_status"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    energy_kwh: Mapped[float]=mapped_column(Float)
    capacity_kwh: Mapped[float]=mapped_column(Float)
    soc: Mapped[float]=mapped_column(Float)
    charge_kw: Mapped[float]=mapped_column(Float)
    discharge_kw: Mapped[float]=mapped_column(Float)
    run_id: Mapped[str]=mapped_column(String(36),nullable=True,index=True)

class Prediction(Base):
    __tablename__="ml_predictions"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    target: Mapped[str]=mapped_column(String(20))
    predicted: Mapped[float]=mapped_column(Float)
    actual: Mapped[float]=mapped_column(Float,nullable=True)
    model_version: Mapped[str]=mapped_column(String(80))
    source: Mapped[str]=mapped_column(String(40),default="simulation")
    run_id: Mapped[str]=mapped_column(String(36),nullable=True,index=True)

class OptimizationResult(Base):
    __tablename__="optimization_results"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    run_id: Mapped[str]=mapped_column(String(36),ForeignKey("simulation_history.id"),index=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    status: Mapped[str]=mapped_column(String(40))
    objective_value: Mapped[float]=mapped_column(Float)
    decision: Mapped[dict]=mapped_column(JSON)

class GridCondition(Base):
    __tablename__="grid_conditions"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    import_kw: Mapped[float]=mapped_column(Float)
    export_kw: Mapped[float]=mapped_column(Float)
    served_kw: Mapped[float]=mapped_column(Float)
    unserved_kw: Mapped[float]=mapped_column(Float)
    available: Mapped[bool]=mapped_column(Boolean)
    status: Mapped[str]=mapped_column(String(40))
    run_id: Mapped[str]=mapped_column(String(36),nullable=True,index=True)

class Anomaly(Base):
    __tablename__="anomalies"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    equipment_id: Mapped[str]=mapped_column(String(80))
    parameter: Mapped[str]=mapped_column(String(80))
    severity: Mapped[str]=mapped_column(String(20))
    score: Mapped[float]=mapped_column(Float)
    message: Mapped[str]=mapped_column(Text)
    action: Mapped[str]=mapped_column(Text)
    acknowledged: Mapped[bool]=mapped_column(Boolean,default=False)
    note: Mapped[str]=mapped_column(Text,default="")
    run_id: Mapped[str]=mapped_column(String(36),nullable=True,index=True)

class EquipmentHealth(Base):
    __tablename__="equipment_health"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime,index=True)
    equipment_id: Mapped[str]=mapped_column(String(80),index=True)
    health_score: Mapped[float]=mapped_column(Float)
    failure_risk: Mapped[float]=mapped_column(Float)
    priority: Mapped[str]=mapped_column(String(20))
    recommendation: Mapped[str]=mapped_column(Text)
    run_id: Mapped[str]=mapped_column(String(36),nullable=True,index=True)

class MaintenanceRecord(Base):
    __tablename__="maintenance_records"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    created_at: Mapped[datetime]=mapped_column(DateTime)
    equipment_id: Mapped[str]=mapped_column(String(80))
    action: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20))

class Configuration(Base):
    __tablename__="user_configuration"
    key: Mapped[str]=mapped_column(String(60),primary_key=True)
    value: Mapped[dict]=mapped_column(JSON)
    updated_at: Mapped[datetime]=mapped_column(DateTime)

from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Literal, Optional

class BatteryConfig(BaseModel):
    capacity_kwh: float = Field(1200, ge=10, le=100000)
    initial_soc: float = Field(62, ge=0, le=100)
    min_soc: float = Field(15, ge=0, le=100)
    max_soc: float = Field(95, gt=0, le=100)
    charge_efficiency: float = Field(.95, gt=.5, le=1)
    discharge_efficiency: float = Field(.95, gt=.5, le=1)
    max_charge_kw: float = Field(300, gt=0, le=50000)
    max_discharge_kw: float = Field(300, gt=0, le=50000)
    @model_validator(mode="after")
    def soc_order(self):
        if self.min_soc >= self.max_soc:
            raise ValueError("Minimum SOC must be below maximum SOC")
        if not self.min_soc <= self.initial_soc <= self.max_soc:
            raise ValueError("Initial SOC must be inside the permitted SOC window")
        return self

class SimulationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["normal", "low_solar", "high_demand", "surplus", "low_battery", "outage", "abnormal"] = "normal"
    horizon: int = Field(24, ge=1, le=48)
    peak_irradiance: float = Field(900, ge=0, le=1400, description="Clear-sky peak W/m²; daylight geometry still applies")
    temperature: Optional[float] = Field(None, ge=-30, le=60)
    cloud_cover: Optional[float] = Field(None, ge=0, le=100)
    wind_speed: Optional[float] = Field(None, ge=0, le=40)
    demand_factor: float = Field(1, ge=.2, le=3)
    battery: BatteryConfig = Field(default_factory=BatteryConfig)
    grid_available: bool = True
    export_enabled: bool = True
    grid_import_limit_kw: float = Field(800, ge=0, le=10000)
    grid_export_limit_kw: float = Field(400, ge=0, le=10000)
    import_tariff: float = Field(.18, ge=0, le=5, description="USD/kWh, illustrative")
    export_tariff: float = Field(.045, ge=0, le=5)
    carbon_factor: float = Field(.71, ge=0, le=2, description="Assumed kg CO2/kWh, not a verified regional factor")
    degradation_cost: float = Field(.015, ge=0, le=1, description="USD per kWh charged plus discharged")
    fault_mode: Literal["none", "voltage_sag", "frequency_deviation", "overload", "combined"] = "none"
    @model_validator(mode="after")
    def presets(self):
        # Named presets are initial conditions, not hardcoded result tables.
        if self.scenario == "low_solar":
            self.peak_irradiance=450; self.cloud_cover=85.0
        elif self.scenario == "high_demand":
            self.demand_factor=1.65
        elif self.scenario == "surplus":
            self.peak_irradiance=1100; self.cloud_cover=5.0; self.wind_speed=11.5; self.demand_factor=.7
        elif self.scenario == "low_battery":
            self.battery.initial_soc=self.battery.min_soc
        elif self.scenario == "outage":
            self.grid_available=False
        elif self.scenario == "abnormal":
            self.fault_mode="combined"; self.demand_factor=1.8
        return self

class StepRequest(BaseModel):
    hours: int = Field(1, ge=1, le=24)

class PredictRequest(BaseModel):
    records: list[dict] = Field(min_length=1, max_length=5000)
    target: Literal["solar", "wind", "load"]

class MaintenanceRequest(BaseModel):
    equipment_id: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=3, max_length=1000)
    status: Literal["planned", "completed"] = "planned"

class AcknowledgeRequest(BaseModel):
    note: str = Field(default="Reviewed by operator", min_length=1, max_length=1000)

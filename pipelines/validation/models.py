from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Intensity(BaseModel):
    forecast: float | None = Field(default=None, ge=0)
    actual: float | None = Field(default=None, ge=0)
    index: str | None = None


class Share(BaseModel):
    fuel: str
    perc: float = Field(ge=0, le=100)


class CarbonInterval(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    start: datetime = Field(alias="from")
    end: datetime = Field(alias="to")
    intensity: Intensity

    @model_validator(mode="after")
    def interval(self):
        if not self.start.tzinfo or not self.end.tzinfo or (self.end - self.start).total_seconds() != 1800:
            raise ValueError("Expected timezone-aware half-hour interval")
        if self.intensity.forecast is None and self.intensity.actual is None:
            raise ValueError("No usable carbon measurement")
        return self


class FuelOutturn(BaseModel):
    startTime: datetime
    publishTime: datetime | None = None
    fuelType: str
    generation: float  # Signed interconnector flows are valid.


class DemandRecord(BaseModel):
    SETTLEMENT_DATE: date
    SETTLEMENT_PERIOD: int = Field(ge=1, le=50)
    ND: float | None = Field(default=None, ge=0)
    TSD: float | None = Field(default=None, ge=0)
    FORECAST_ACTUAL_INDICATOR: str = "A"  # Verified historic-demand resources contain outturn only.

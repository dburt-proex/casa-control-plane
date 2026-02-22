from dataclasses import dataclass


@dataclass
class Signals:
    financial: float
    legal: float
    brand: float
    operational: float
    cognitive: float

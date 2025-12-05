from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json
from backend.timeframe import TimeFrame

@dataclass
class SerializableCalculatedField:
    name: str
    field_type: str  # e.g. "sma", "percentile", "is_above_ma"
    params: Dict[str, Any]
    dependencies: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SerializableCalculatedField":
        return SerializableCalculatedField(
            name=d["name"],
            field_type=d["field_type"],
            params=d.get("params", {}),
            dependencies=d.get("dependencies", []),
        )

    def save_to_path(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, default=str)

    @staticmethod
    def load_from_path(path: str) -> "SerializableCalculatedField":
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return SerializableCalculatedField.from_dict(d)

@dataclass
class StrategySpec:
    name: str
    ticker: str
    timeframe_json: str  # produced by TimeFrame.to_json()
    trigger_expr: str  # simple string expression (e.g. "Close > MA50")
    debounce: int = 0
    offset: int = 0
    exit_after: Optional[int] = None
    calculated_fields: List[SerializableCalculatedField] = None

    def to_json(self) -> str:
        d = asdict(self)
        d["calculated_fields"] = [cf.to_dict() for cf in (self.calculated_fields or [])]
        return json.dumps(d, default=str)

    @staticmethod
    def from_json(s: str) -> "StrategySpec":
        d = json.loads(s)
        cfs = [SerializableCalculatedField.from_dict(x) for x in d.get("calculated_fields", [])]
        return StrategySpec(
            name=d["name"],
            ticker=d["ticker"],
            timeframe_json=d["timeframe_json"],
            trigger_expr=d.get("trigger_expr", ""),
            debounce=d.get("debounce", 0),
            offset=d.get("offset", 0),
            exit_after=d.get("exit_after"),
            calculated_fields=cfs,
        )

    def get_timeframe(self) -> TimeFrame:
        return TimeFrame.from_json(self.timeframe_json)

    @staticmethod
    def save_to_path(spec: "StrategySpec", path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(spec.to_json())

    @staticmethod
    def load_from_path(path) -> "StrategySpec":
        with open(path, "r", encoding="utf-8") as f:
            return StrategySpec.from_json(f.read())

# New dataclasses for user-created Products and Triggers
@dataclass
class ProductSpec:
    name: str
    components: Dict[str, float]  # ticker -> weight (weights should sum to 1.0)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(s: str) -> "ProductSpec":
        d = json.loads(s)
        return ProductSpec(name=d["name"], components=d.get("components", {}))

    @staticmethod
    def save_to_path(spec: "ProductSpec", path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(spec.to_json())

    @staticmethod
    def load_from_path(path) -> "ProductSpec":
        with open(path, "r", encoding="utf-8") as f:
            return ProductSpec.from_json(f.read())

@dataclass
class TriggerSpec:
    name: str
    expression: str
    debounce: int = 0
    offset: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(s: str) -> "TriggerSpec":
        d = json.loads(s)
        return TriggerSpec(name=d["name"], expression=d.get("expression",""), debounce=int(d.get("debounce",0)), offset=int(d.get("offset",0)))

    @staticmethod
    def save_to_path(spec: "TriggerSpec", path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(spec.to_json())

    @staticmethod
    def load_from_path(path) -> "TriggerSpec":
        with open(path, "r", encoding="utf-8") as f:
            return TriggerSpec.from_json(f.read())

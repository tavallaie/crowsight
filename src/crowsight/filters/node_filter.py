from dataclasses import dataclass, field
from enum import Enum, auto
import re
from typing import List, Optional, Dict, Any, Pattern


class NodeCategory(Enum):
    FUNCTION = auto()
    IMPORT = auto()
    CALL = auto()
    CLASS = auto()
    COMMENT = auto()
    LITERAL = auto()
    VARIABLE = auto()
    RAW = auto()


@dataclass
class NodeFilter:
    types: List[NodeCategory] = field(default_factory=list)
    raw_types: List[str] = field(default_factory=list)
    pattern: Optional[Pattern] = None
    languages: Optional[List[str]] = None
    min_args: Optional[int] = None
    max_args: Optional[int] = None
    gte: Dict[str, float] = field(default_factory=dict)
    lte: Dict[str, float] = field(default_factory=dict)
    eq: Dict[str, Any] = field(default_factory=dict)
    neq: Dict[str, Any] = field(default_factory=dict)
    include_node: bool = False

    @classmethod
    def from_kwargs(cls, **kwargs):
        pat = re.compile(kwargs["pattern"]) if kwargs.get("pattern") else None
        return cls(
            types=kwargs.get("types", []),
            raw_types=kwargs.get("raw_types", []),
            pattern=pat,
            languages=kwargs.get("languages"),
            min_args=kwargs.get("min_args"),
            max_args=kwargs.get("max_args"),
            gte=kwargs.get("gte", {}),
            lte=kwargs.get("lte", {}),
            eq=kwargs.get("eq", {}),
            neq=kwargs.get("neq", {}),
            include_node=kwargs.get("include_node", False),
        )

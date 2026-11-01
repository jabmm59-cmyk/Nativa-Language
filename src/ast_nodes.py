from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


@dataclass
class Node:
    line: int = field(default=0, kw_only=True)
    col: int = field(default=0, kw_only=True)


@dataclass
class Param:
    name: str
    default: Optional[Node]
    vararg: bool = False


@dataclass
class Program(Node):
    body: List[Node]


@dataclass
class Num(Node):
    value: Any


@dataclass
class Str(Node):
    value: str


@dataclass
class Interp(Node):
    parts: List[Any]


@dataclass
class Const(Node):
    value: Any


@dataclass
class Name(Node):
    id: str


@dataclass
class ListLit(Node):
    items: List[Node]


@dataclass
class DictLit(Node):
    pairs: List[Tuple[Node, Node]]


@dataclass
class Unary(Node):
    op: str
    operand: Node


@dataclass
class BinOp(Node):
    op: str
    left: Node
    right: Node


@dataclass
class BoolOp(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Compare(Node):
    left: Node
    ops: List[str]
    rights: List[Node]


@dataclass
class Call(Node):
    func: Node
    args: List[Node]
    kwargs: List[Tuple[str, Node]]


@dataclass
class Index(Node):
    obj: Node
    index: Node


@dataclass
class Attr(Node):
    obj: Node
    name: str


@dataclass
class Utype(Node):
    prompt: Optional[Node]


@dataclass
class Assign(Node):
    target: Node
    value: Node


@dataclass
class ExprStmt(Node):
    expr: Node


@dataclass
class Shw(Node):
    args: List[Node]
    kwargs: List[Tuple[str, Node]]


@dataclass
class If(Node):
    test: Node
    body: List[Node]
    orelse: List[Node]


@dataclass
class While(Node):
    test: Node
    body: List[Node]


@dataclass
class For(Node):
    var: str
    iterable: Node
    body: List[Node]


@dataclass
class FuncDef(Node):
    name: str
    params: List[Param]
    body: List[Node]


@dataclass
class Return(Node):
    value: Optional[Node]


@dataclass
class Break(Node):
    pass


@dataclass
class Continue(Node):
    pass


@dataclass
class ClassDef(Node):
    name: str
    bases: List[Node]
    body: List[Node]


@dataclass
class Import(Node):
    names: List[Tuple[str, Optional[str]]]  # (module_name, alias)


@dataclass
class ImportFrom(Node):
    module: str
    names: List[Tuple[str, Optional[str]]]  # (name, alias)
    level: int = 0


@dataclass
class Try(Node):
    body: List[Node]
    handlers: List['ExceptHandler']
    finalbody: List[Node]


@dataclass
class ExceptHandler(Node):
    type: Optional[Node]  # exception type to catch (None = catch all)
    name: Optional[str]   # variable name to bind exception
    body: List[Node]


@dataclass
class Raise(Node):
    exc: Optional[Node]  # exception to raise (None = re-raise)

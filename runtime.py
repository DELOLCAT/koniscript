from typing import Any
class BuiltinFunction:
    def __init__(self, name, func):
        self.name = name
        self.func = func

    def __call__(self, *args) -> Any:
        return self.func(*args)
    def __repr__(self) -> str:
        return f"BuiltinFunction({self.name}, {self.func})"

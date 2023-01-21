from dataclasses import dataclass
from numbers import Number


@dataclass
class DataOption:
    name: str


@dataclass
class NumericOption(DataOption):
    value: Number
    min: Number
    max: Number


@dataclass
class ListOptionPair:
    name: str
    value: str


@dataclass
class ListOption(DataOption):
    options: list[ListOptionPair]

    def value_to_name(self, value: str) -> str:
        for option in self.options:
            if option.value == value:
                return option.name


@dataclass
class BoolOption(DataOption):
    checked: bool

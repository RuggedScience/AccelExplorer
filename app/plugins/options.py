from dataclasses import dataclass


@dataclass
class DataOption:
    name: str


@dataclass
class NumericOption(DataOption):
    value: int | float
    min: int | float
    max: int | float


@dataclass
class ListOptionPair:
    name: str
    value: str


@dataclass
class ListOption(DataOption):
    options: list[ListOptionPair]

    def value_to_name(self, value: str) -> str | None:
        for option in self.options:
            if option.value == value:
                return option.name


@dataclass
class BoolOption(DataOption):
    checked: bool

from collections import namedtuple
from dataclasses import dataclass
from numbers import Number
from typing import List


@dataclass
class DataOption:
    name: str


@dataclass
class NumericOption(DataOption):
    value: Number
    min: Number
    max: Number


ListOptionPair = namedtuple("ListOptionPair", ["name", "value"])


@dataclass
class ListOption(DataOption):

    options: List[ListOptionPair]


@dataclass
class BoolOption(DataOption):
    checked: bool

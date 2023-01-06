from numbers import Number
from typing import List, Tuple
from dataclasses import dataclass
from collections import namedtuple


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

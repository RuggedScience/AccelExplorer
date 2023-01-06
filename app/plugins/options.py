from numbers import Number
from typing import List
from dataclasses import dataclass


@dataclass
class DataOption:
    name: str


@dataclass
class NumericOption(DataOption):
    value: Number
    min: Number
    max: Number


@dataclass
class ListOption(DataOption):
    options: List[str]

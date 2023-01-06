from numbers import Number


class DataOption:
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class NumericOption(DataOption):
    def __init__(self, name: str, value: Number, min: Number, max: Number):
        super().__init__(name)
        self._value = value
        self._min = min
        self._max = max

    @property
    def value(self) -> Number:
        return self._value

    @property
    def min(self) -> Number:
        return self._min

    @property
    def max(self) -> Number:
        return self._max

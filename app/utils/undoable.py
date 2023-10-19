from functools import wraps, partial

from collections.abc import Callable

from PySide6.QtGui import QUndoCommand


class GenericCommand(QUndoCommand):
    def __init__(
        self,
        title: str,
        undo: Callable[[], None],
        redo: Callable[[], None],
        parent: QUndoCommand | None = None,
    ):
        super().__init__(title, parent)
        self._undo = undo
        self._redo = redo

    def undo(self) -> None:
        self._undo()

    def redo(self) -> None:
        self._redo()


def undoable(
    value_attr: str,
    title: str | None = None,
    title_arg: str | None = None,
    new_value_arg: str | int = 1,
    remove_title_arg: bool = False,
    undo_stack_attr: str = "undo_stack",
):
    """Decorator for automatically making methods undoable"""

    def inner(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            self = args[0]
            undo = kwargs.pop("undo", True)
            old_value = None
            if undo:
                old_value = getattr(self, value_attr)
                if callable(old_value):
                    old_value = old_value()

                if isinstance(new_value_arg, str):
                    new_value = kwargs.pop(new_value_arg)
                elif isinstance(new_value_arg, int):
                    new_value = args[new_value_arg]
                else:
                    raise TypeError(
                        f"new_value_arg must be string or int, not {type(new_value_arg)}"
                    )

                # Try to compare the new and old values.
                # If they don't support comparison just
                # assume the values changed
                try:
                    if old_value == new_value:
                        return
                except Exception:
                    pass

                formatted_title = ""
                if title_arg is not None:
                    if isinstance(title_arg, str):
                        formatted_title = kwargs.get(title_arg, "")
                        if remove_title_arg and title_arg in kwargs:
                            del kwargs[title_arg]
                    else:
                        raise TypeError(
                            f"title_arg must be string or int, not {type(title_arg)}"
                        )
                elif title:
                    formatted_title = title.format(
                        old_value=old_value, new_value=new_value
                    )

                undo_func = partial(f, self, old_value)
                redo_func = partial(f, self, new_value)
                cmd = GenericCommand(formatted_title, undo_func, redo_func)

                undo_stack = getattr(self, undo_stack_attr)
                if callable(undo_stack):
                    undo_stack = undo_stack()

                undo_stack.push(cmd)

            else:
                return f(*args, **kwargs)

        return wrap

    return inner

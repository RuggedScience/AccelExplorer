from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
)
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QStyle

from app.views import ViewController, ViewModel, ViewSeries


class ViewsTreeWidget(QTreeWidget):
    currentViewChanged = Signal(ViewController, ViewController)
    viewSelectionChanged = Signal(list)
    seriesHovered = Signal(ViewSeries, ViewSeries)

    current_view_color = QColor(235, 177, 133)

    def __init__(self, parent: Optional[QWidget] = ...) -> None:
        super().__init__(parent)

        self.viewport().setMouseTracking(True)

        self.currentItemChanged.connect(self._current_item_changed)
        self.itemSelectionChanged.connect(self._selection_changed)
        self.itemClicked.connect(self._item_clicked)

        self.setDragDropMode(QTreeWidget.DragDropMode.DragDrop)
        self.setEditTriggers(QTreeWidget.EditTrigger.DoubleClicked)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.itemChanged.connect(self._item_changed)

        self._controllers: dict[QTreeWidgetItem, ViewController] = {}

        self._drag_model = None
        self._hovered_series = None
        self._current_controller = None

    def add_view(self, controller: ViewController) -> None:
        items = [controller.tree_item] + [view.tree_item for view in controller]
        for item in items:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self._controllers[controller.tree_item] = controller

    def remove_view(self, controller: ViewController) -> None:
        item = controller.tree_item
        self._controllers.pop(item)
        self.invisibleRootItem().removeChild(item)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_model = None
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        new_series = None
        controller = None
        if event.buttons() == Qt.MouseButton.NoButton:
            item = self.itemAt(event.pos())
            controller = self.get_controller(item)

            if controller and item in controller:
                new_series = controller[item]

        if new_series != self._hovered_series:
            self.seriesHovered.emit(new_series, self._hovered_series)
            self._hovered_series = new_series

        return super().mouseMoveEvent(event)

    def _drop_is_valid(self, controller: ViewController) -> bool:
        return (
            controller
            and controller not in self.get_selected_controllers()
            and controller.model.can_merge(self._drag_model)
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.source() is self:
            self._drag_model = ViewModel()
            controllers = self.get_selected_controllers()
            for controller in controllers:
                model = controller.model.copy()
                if not controller.tree_item.isSelected():
                    cols = []
                    for col in model.df:
                        if col in controller:
                            if controller[col].tree_item.isSelected():
                                cols.append(col)
                    model = controller.model[cols]

                if not self._drag_model.can_merge(model):
                    self._drag_model = None
                    event.ignore()
                    return

                model.add_suffix(f" - {controller.name}")
                self._drag_model.merge(model)
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        super().dragMoveEvent(event)

        drop_item = self.itemAt(event.pos())
        drop_controller = self.get_controller(drop_item)
        if self._drop_is_valid(drop_controller):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        drop_item = self.itemAt(event.pos())
        drop_controller = self.get_controller(drop_item)
        if self._drop_is_valid(drop_controller):
            model = drop_controller.model.copy()
            model.merge(self._drag_model)
            drop_controller.set_model(model, title="Combined views")
            event.acceptProposedAction()
            self.setCurrentItem(drop_item)
        else:
            event.ignore()

    def _item_changed(self, item: QTreeWidgetItem, col: int) -> None:
        if col == 0:
            parent = self._get_root_parent(item)
            controller = self.get_controller(item)
            if controller:
                if parent is item:
                    controller.set_name(item.text(0))
                elif item in controller:
                    series = controller[item]
                    series.set_name(item.text(0))
                    controller[item].chart_series.setVisible(
                        item.checkState(0) == Qt.Checked
                    )

    def _current_item_changed(self, current: QTreeWidgetItem, _) -> None:
        new = self.get_controller(current)
        if new != self._current_controller:
            old = self._current_controller
            self._current_controller = new
            self.currentViewChanged.emit(new, old)

            columns = self.columnCount()
            if new:
                for col in range(columns):
                    new.tree_item.setBackground(col, self.current_view_color)

            if old:
                for col in range(columns):
                    old.tree_item.setBackground(col, QBrush())

    def _selection_changed(self) -> None:
        controllers = self.get_selected_controllers()
        self.viewSelectionChanged.emit(controllers)

    def _get_root_parent(self, item):
        while item and item.parent() is not None:
            item = item.parent()
        return item

    def get_controller(self, item: QTreeWidgetItem) -> ViewController:
        if item not in self._controllers:
            item = self._get_root_parent(item)

        if item:
            return self._controllers.get(item)
        return None

    def get_current_controller(self) -> ViewController:
        return self.get_controller(self.currentItem())

    def get_selected_controllers(self) -> list[ViewController]:
        controllers = []
        for item in self.selectedItems():
            controllers.append(self.get_controller(item))

        return list(set(controllers))

    def _item_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        controller = self.get_controller(item)
        # Automatically select / deselect all series when a view is selected / deselected
        if controller and item is controller.tree_item:
            for series in controller:
                series.tree_item.setSelected(item.isSelected())

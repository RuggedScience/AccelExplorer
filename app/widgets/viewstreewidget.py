from typing import Optional, Dict, List

from PySide6.QtCore import Qt, Signal, QItemSelection
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent

from app.viewcontroller import ViewController


class ViewsTreeWidget(QTreeWidget):
    currentViewChanged = Signal(ViewController, ViewController)
    selectionChanged = Signal(list)

    def __init__(self, parent: Optional[QWidget] = ...) -> None:
        super().__init__(parent)

        self.currentItemChanged.connect(self._current_item_changed)
        self.itemSelectionChanged.connect(self._selection_changed)

        self.setDragDropMode(QTreeWidget.DragDropMode.DragDrop)
        self.setEditTriggers(QTreeWidget.EditTrigger.DoubleClicked)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.itemChanged.connect(self._item_changed)

        self._drag_dfs = None
        self._controllers: Dict[QTreeWidgetItem, ViewController] = {}

    def add_view(self, controller: ViewController) -> None:
        items = [controller.tree_item] + [view.tree_item for view in controller]
        for item in items:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self._controllers[controller.tree_item] = controller

    def remove_view(self, controller: ViewController) -> None:
        item = controller.tree_item
        self._controllers.pop(item)
        self.invisibleRootItem().removeChild(item)

    def remove_current_view(self) -> ViewController:
        controller = self.get_current_controller()
        if controller:
            self.remove_view(controller)
            item = controller.tree_item
            next_item = self.itemAbove(item)
            next_item = self._get_root_parent(next_item)

            if self.currentItem() is None:
                self.setCurrentItem(next_item)

        return controller

    def mousePressEvent(self, event: QMouseEvent) -> None:
        controllers = self.get_selected_controllers()
        self._drag_dfs = {}
        for controller in controllers:
            df = controller.df
            cols = []
            for col in df:
                if col in controller:
                    if controller[col].tree_item.isSelected():
                        cols.append(col)

            self._drag_dfs[controller] = df[cols]

        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_dfs = None
        return super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        return super().dragEnterEvent(event)

    def _drag_is_valid(self) -> bool:
        return bool(self._drag_dfs)

    def _drop_is_valid(self, controller: ViewController) -> bool:
        return (
            controller
            and controller not in self._drag_dfs
            and controller.can_add_data(self._drag_dfs.values())
        )

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        super().dragMoveEvent(event)

        if self._drag_is_valid():
            drop_item = self.itemAt(event.pos())
            drop_controller = self.get_controller(drop_item)
            if self._drop_is_valid(drop_controller):
                event.acceptProposedAction()
                return

        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if self._drag_is_valid():
            drop_item = self.itemAt(event.pos())
            drop_controller = self.get_controller(drop_item)
            if self._drop_is_valid(drop_controller):
                for controller, df in self._drag_dfs.items():
                    drop_controller.add_data(controller.name, df)
                event.acceptProposedAction()
                self.setCurrentItem(drop_item)
                return

        event.ignore()

    def _item_changed(self, item: QTreeWidgetItem, col: int) -> None:
        if col == 0:
            parent = self._get_root_parent(item)
            controller = self.get_controller(item)
            if controller:
                if parent is item:
                    controller.name = item.text(0)
                elif item in controller:
                    controller.rename_series(item, item.text(0))
                    controller[item].chart_series.setVisible(
                        item.checkState(0) == Qt.Checked
                    )

    def _current_item_changed(
        self, current: QTreeWidgetItem, previous: QTreeWidgetItem
    ) -> None:
        new = self.get_controller(current)
        old = self.get_controller(previous)
        self.currentViewChanged.emit(new, old)

    def _selection_changed(self) -> None:
        controllers = self.get_selected_controllers()
        self.selectionChanged.emit(controllers)

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

    def get_selected_controllers(self) -> List[ViewController]:
        controllers = []
        for item in self.selectedItems():
            controllers.append(self.get_controller(item))

        return list(set(controllers))

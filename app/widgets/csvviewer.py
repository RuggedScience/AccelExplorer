from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PySide6.QtGui import (
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QColor,
    QTextFormat,
    QTextCursor,
)
from PySide6.QtCore import QRect, Qt, Signal, QSize


class LineNumberArea(QWidget):
    def __init__(self, viewer: "CSVViewer") -> None:
        super().__init__(viewer)
        self._viewer = viewer

    def sizeHint(self) -> QSize:
        return QSize(self._viewer.lineNumberAreaWidth(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._viewer.lineNumberAreaPaintEvent(event)


class CSVViewer(QPlainTextEdit):
    lineNumberChanged = Signal(int)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._lineNumberArea = LineNumberArea(self)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self._handle_cursor_changed)

        self.viewport().setCursor(Qt.ArrowCursor)
        self.updateLineNumberAreaWidth(0)
        self._line_number = None

    def setPlainText(self, text: str) -> None:
        # Reset line number when text is reset
        self._line_number = None
        return super().setPlainText(text)

    def setCurrentLine(self, line: int) -> None:
        if line == self._line_number:
            return

        block = self.document().findBlockByLineNumber(line - 1)
        cursor = QTextCursor(block)
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def lineNumberAreaPaintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self._lineNumberArea)
        painter.fillRect(event.rect(), Qt.lightGray)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.black)
                painter.drawText(
                    0,
                    top,
                    self._lineNumberArea.width(),
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber += 1

        painter.end()

    def lineNumberAreaWidth(self) -> int:
        digits = 1
        m = max(1, self.blockCount())
        while m >= 10:
            m /= 10
            digits += 1

        space = 3 + self.fontMetrics().horizontalAdvance("9") * digits
        return int(space)

    def updateLineNumberAreaWidth(self, newBlockCount: int) -> None:
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect: QRect, dy: int) -> None:
        if dy:
            self._lineNumberArea.scroll(0, dy)
        else:
            self._lineNumberArea.update(
                0, rect.y(), self._lineNumberArea.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def _handle_cursor_changed(self) -> None:
        cursor = self.textCursor()

        line_number = cursor.blockNumber() + 1
        if line_number == self._line_number:
            return

        extraSelections = []

        selection = QTextEdit.ExtraSelection()
        lineColor = QColor(Qt.yellow).lighter(160)

        selection.format.setBackground(lineColor)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)

        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor
        )
        # Select one extra character to allow the full line to be highlighted
        cursor.movePosition(
            QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor
        )

        selection.cursor = cursor

        extraSelections.append(selection)

        self.setExtraSelections(extraSelections)
        self._line_number = line_number
        self.lineNumberChanged.emit(line_number)

    def resizeEvent(self, e: QResizeEvent) -> None:
        super().resizeEvent(e)

        cr = self.contentsRect()
        self._lineNumberArea.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )

from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PySide6.QtGui import QPainter, QPaintEvent, QResizeEvent, QColor, QTextFormat
from PySide6.QtCore import QRect, Qt

from .linenumberarea import LineNumberArea

class CSVViewer(QPlainTextEdit):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._lineNumberArea = LineNumberArea(self)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlighCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlighCurrentLine()

    def lineNumberAreaPaintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self._lineNumberArea)
        painter.fillRect(event.rect(), Qt.lightGray)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, top, self._lineNumberArea.width(), self.fontMetrics().height(), Qt.AlignRight, number)

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

        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return int(space)

    def updateLineNumberAreaWidth(self, newBlockCount: int) -> None:
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect: QRect, dy: int) -> None:
        if dy:
            self._lineNumberArea.scroll(0, dy)
        else:
            self._lineNumberArea.update(0, rect.y(), self._lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def highlighCurrentLine(self) -> None:
        extraSelections = self.extraSelections()

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            
            lineColor = QColor(Qt.yellow).lighter(160)

            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)

        self.setExtraSelections(extraSelections)

    def resizeEvent(self, e: QResizeEvent) -> None:
        super().resizeEvent(e)

        cr = self.contentsRect()
        self._lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

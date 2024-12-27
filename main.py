import sys
import zipfile
import os
import tempfile
import threading
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QFileDialog, QVBoxLayout, QWidget,
    QMenuBar, QMessageBox, QPushButton, QHBoxLayout, QPlainTextEdit, QLabel,
    QTreeView, QSplitter, QCompleter, QListView, QFrame, QScrollBar, QTextEdit, QTabWidget, QTabBar
)
from PyQt6.QtGui import QIcon, QAction, QFileSystemModel, QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter, QTextFormat
from PyQt6.QtCore import Qt, QDir, QRegularExpression, QStringListModel, QRect, QSize, QProcess, QThread, pyqtSignal, QEvent
from frenpy import load, compile_frenpy, get_words_frenpy

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("white"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = get_words_frenpy()
        for keyword in keywords:
            pattern = QRegularExpression(f"\\b{keyword}\\b")
            self.highlighting_rules.append((pattern, keyword_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("magenta"))
        self.highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("green"))
        self.highlighting_rules.append((QRegularExpression(r"#.*"), comment_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            match_iterator = expression.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

class AutoCompleter(QCompleter):
    def __init__(self, keywords, parent=None):
        super().__init__(keywords, parent)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.popup().setStyleSheet("background-color: #2b2b2b; color: white;")

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self):
        digits = 1
        max_block = max(1, self.blockCount())
        while max_block >= 10:
            max_block //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(0, top, self.line_number_area.width(), self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(Qt.GlobalColor.white)
            line_color.setAlphaF(0.1)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return:
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.StartOfLine, cursor.MoveMode.KeepAnchor)
            line_text = cursor.selectedText()
            super().keyPressEvent(event)
            if line_text.strip().endswith(":"):
                cursor = self.textCursor()
                cursor.insertText(" " * 4)
                self.setTextCursor(cursor)
        elif event.key() in (Qt.Key.Key_ParenLeft, Qt.Key.Key_BraceLeft, Qt.Key.Key_BracketLeft, Qt.Key.Key_QuoteDbl, Qt.Key.Key_Apostrophe):
            char_map = {
                Qt.Key.Key_ParenLeft: '()',
                Qt.Key.Key_BraceLeft: '{}',
                Qt.Key.Key_BracketLeft: '[]',
                Qt.Key.Key_QuoteDbl: '""',
                Qt.Key.Key_Apostrophe: "''"
            }
            cursor = self.textCursor()
            cursor.insertText(char_map[event.key()])
            cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor)
            self.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)

class ScriptRunner(QThread):
    output_signal = pyqtSignal(str)
    input_signal = pyqtSignal(str)
    started_signal = pyqtSignal()
    finished_signal = pyqtSignal()

    def __init__(self, script_path):
        super().__init__()
        self.script_path = script_path
        self.process = None

    def run(self):
        self.started_signal.emit()
        self.process = QProcess()
        self.process.setProgram("python")
        self.process.setArguments([self.script_path])
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(lambda: self.output_signal.emit(self.process.readAllStandardOutput().data().decode()))
        self.process.readyReadStandardError.connect(lambda: self.output_signal.emit(self.process.readAllStandardError().data().decode()))
        self.process.start()
        self.process.waitForFinished()
        self.finished_signal.emit()

    def stop(self):
        if self.process:
            self.process.kill()
            self.finished_signal.emit()

    def write_input(self, text):
        if self.process:
            self.process.write(text.encode())
            self.process.write(b'\n')

class FrenpyIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.script_runner = None
        self.script_running = False

    def init_ui(self):
        self.setWindowTitle("Frenpy IDE")
        self.setGeometry(100, 100, 1200, 800) 

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter)

        self.model = QFileSystemModel()
        self.model.setRootPath("")

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index("")) 
        self.tree.clicked.connect(self.on_tree_view_clicked)
        self.tree.setMinimumWidth(200) 
        splitter.addWidget(self.tree)

        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        splitter.addWidget(main_area)

        self.current_file_label = QLabel("Aucun fichier sélectionné", self)
        main_layout.addWidget(self.current_file_label)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.update_current_file_label)
        main_layout.addWidget(self.tab_widget)

        self.create_menu_bar()

        self.console_output = QPlainTextEdit(self)
        self.console_output.setReadOnly(False)
        self.console_output.installEventFilter(self)
        main_layout.addWidget(self.console_output)

        button_layout = QHBoxLayout()

        run_button = QPushButton("Run Script", self)
        run_button.clicked.connect(self.run_script)
        button_layout.addWidget(run_button)

        stop_button = QPushButton("Stop Script", self)
        stop_button.clicked.connect(self.stop_script)
        button_layout.addWidget(stop_button)

        main_layout.addLayout(button_layout)

        self.console_output.appendPlainText("Aucun espace de travail sélectionné.")

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        open_action = QAction("&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_all_action = QAction("&Save All", self)
        save_all_action.triggered.connect(self.save_all_files)
        file_menu.addAction(save_all_action)

        save_remaining_action = QAction("&Save Remaining Files", self)
        save_remaining_action.triggered.connect(self.save_remaining_files)
        file_menu.addAction(save_remaining_action)

        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        workspace_menu = menu_bar.addMenu("&Workspace")

        open_workspace_action = QAction("&Open Workspace", self)
        open_workspace_action.triggered.connect(self.open_workspace)
        workspace_menu.addAction(open_workspace_action)

        export_workspace_action = QAction("&Export Workspace as ZIP", self)
        export_workspace_action.triggered.connect(self.export_workspace)
        workspace_menu.addAction(export_workspace_action)

    def new_file(self):
        editor = CodeEditor()
        self.highlighter = PythonHighlighter(editor.document())
        self.tab_widget.addTab(editor, "Untitled")
        self.tab_widget.setCurrentWidget(editor)
        self.current_file_label.setText("Aucun fichier sélectionné")

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Frenpy files (*.frenpy);;All Files (*)")
        if file_path:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                editor = CodeEditor()
                editor.setPlainText(content)
                self.highlighter = PythonHighlighter(editor.document())
                self.tab_widget.addTab(editor, os.path.basename(file_path))
                self.tab_widget.setCurrentWidget(editor)
            self.current_file_label.setText(file_path)

    def save_file(self):
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Frenpy files (*.frenpy);;All Files (*)")
            if file_path:
                with open(file_path, "w") as file:
                    content = current_editor.toPlainText()
                    file.write(content)
                self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(file_path))
                self.current_file_label.setText(file_path)

    def save_all_files(self):
        for index in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(index)
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Frenpy files (*.frenpy);;All Files (*)")
            if file_path:
                with open(file_path, "w") as file:
                    content = editor.toPlainText()
                    file.write(content)
                self.tab_widget.setTabText(index, os.path.basename(file_path))

    def save_remaining_files(self):
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            appdata_path = os.path.join(os.getenv('APPDATA'), 'frenpy_ide')
            os.makedirs(appdata_path, exist_ok=True)
            file_path = os.path.join(appdata_path, 'remaining_files.frenpy')
            with open(file_path, "w") as file:
                content = current_editor.toPlainText()
                file.write(content)
            self.console_output.appendPlainText(f"Fichiers restants enregistrés: {file_path}")

    def run_script(self):
        """Runs the current script using Frenpy."""
        if self.script_running:
            self.console_output.appendPlainText("Un script est déjà en cours d'exécution.")
            return
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            script_content = current_editor.toPlainText()
            if script_content:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".frenpy", mode='w', encoding='utf-8') as temp_file:
                    temp_file.write(script_content)
                    temp_file_path = temp_file.name
                compiled_code = compile_frenpy(temp_file_path)
                if compiled_code:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode='w', encoding='utf-8') as compiled_file:
                        compiled_file.write(compiled_code)
                        compiled_file_path = compiled_file.name
                    self.script_runner = ScriptRunner(compiled_file_path)
                    self.script_runner.output_signal.connect(self.console_output.appendPlainText)
                    self.script_runner.started_signal.connect(self.on_script_started)
                    self.script_runner.finished_signal.connect(self.on_script_finished)
                    self.script_runner.start()
                    os.remove(temp_file_path)

    def stop_script(self):
        if self.script_running:
            self.script_runner.stop()
            self.script_running = False

    def on_script_started(self):
        self.script_running = True
        self.console_output.appendPlainText("Le script a été lancé.")

    def on_script_finished(self):
        self.script_running = False
        self.console_output.appendPlainText("Le script a été arrêté.")

    def on_tree_view_clicked(self, index):
        file_path = self.model.filePath(index)
        if QDir(file_path).exists():
            return 
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            editor = CodeEditor()
            editor.setPlainText(content)
            self.highlighter = PythonHighlighter(editor.document())
            self.tab_widget.addTab(editor, os.path.basename(file_path))
            self.tab_widget.setCurrentWidget(editor)
        self.current_file_label.setText(file_path)

    def close_tab(self, index):
        self.tab_widget.removeTab(index)

    def update_current_file_label(self, index):
        if index != -1:
            editor = self.tab_widget.widget(index)
            file_path = self.tab_widget.tabText(index)
            self.current_file_label.setText(file_path)
        else:
            self.current_file_label.setText("Aucun fichier sélectionné")

    def open_workspace(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Open Workspace", "")
        if dir_path:
            self.tree.setRootIndex(self.model.index(dir_path))
            self.console_output.appendPlainText(f"Espace de travail ouvert: {dir_path}")

    def export_workspace(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Workspace to Export", "")
        if dir_path:
            zip_path, _ = QFileDialog.getSaveFileName(self, "Save Workspace as ZIP", "", "ZIP files (*.zip);;All Files (*)")
            if zip_path:
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for root, dirs, files in os.walk(dir_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, dir_path))
                self.console_output.appendPlainText(f"Espace de travail exporté: {zip_path}")

    def text_changed(self):
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            cursor = current_editor.textCursor()
            cursor.select(cursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText()
            if word:
                self.completer.setCompletionPrefix(word)
                self.completer.complete()

    def insert_completion(self, completion):
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            cursor = current_editor.textCursor()
            cursor.select(cursor.SelectionType.WordUnderCursor)
            cursor.insertText(completion)
            current_editor.setTextCursor(cursor)

    def eventFilter(self, obj, event):
        if obj == self.console_output and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return:
                cursor = self.console_output.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.console_output.setTextCursor(cursor)
                text = self.console_output.toPlainText().split('\n')[-1]
                self.console_output.appendPlainText('')
                if self.script_runner:
                    self.script_runner.write_input(text)
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        try:
            if self.script_running and self.script_runner:
                self.script_runner.stop()
            event.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la fermeture: {str(e)}")
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ide = FrenpyIDE()
    ide.show()
    try:
        sys.exit(app.exec())
    except Exception as e:
        print(f"Erreur lors de l'exécution de l'application: {str(e)}")


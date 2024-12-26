import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QTextEdit, QPushButton, QVBoxLayout, QWidget
import frenpy
import io
import contextlib

frenpy_template = """
# frenpy template
afficher("Hello, World!")
# frenpy config :
frpy_info
frpy_scc="false" # Sauvegarder le fichier compilé
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FrenPY GUI")
        
        self.layout = QVBoxLayout()
        
        self.open_button = QPushButton("Ouvrir un fichier .frenpy")
        self.open_button.clicked.connect(self.open_file)
        self.layout.addWidget(self.open_button)
        
        self.compile_button = QPushButton("Compiler le fichier .frenpy")
        self.compile_button.clicked.connect(self.compile_file)
        self.layout.addWidget(self.compile_button)
        
        self.run_button = QPushButton("Exécuter le fichier compilé")
        self.run_button.clicked.connect(self.run_file)
        self.layout.addWidget(self.run_button)
        
        self.create_button = QPushButton("Créer un fichier .frenpy")
        self.create_button.clicked.connect(self.create_file)
        self.layout.addWidget(self.create_button)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.layout.addWidget(self.console)
        
        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)
        
        self.current_file = None

    def open_file(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Ouvrir un fichier .frenpy", "", "FrenPY Files (*.frenpy)")
        if file_path:
            self.current_file = file_path
            self.console.append(f"Fichier ouvert: {file_path}")

    def compile_file(self):
        if self.current_file:
            compiled_content = frenpy.compile_frenpy(self.current_file)
            if compiled_content is not None:
                save_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le fichier compilé", "", "Compiled Files (*.py)")
                if save_path:
                    with open(save_path, 'w') as file:
                        file.write(compiled_content)
                    self.console.append(f"Fichier compilé et enregistré: {save_path}")
            else:
                self.console.append("Erreur lors de la compilation du fichier.")
        else:
            self.console.append("Aucun fichier .frenpy ouvert.")

    def run_file(self):
        if self.current_file:
            self.console.append(f"Exécution du fichier: {self.current_file}")
            try:
                with open(self.current_file, 'r', encoding='utf-8') as file:
                    code = file.read()
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        exec(code, {'__name__': '__main__'})
                    self.console.append(output.getvalue())
            except Exception as e:
                self.console.append(f"Erreur lors de l'exécution: {e}")
        else:
            self.console.append("Aucun fichier .frenpy ouvert.")

    def create_file(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le fichier .frenpy", "", "FrenPY Files (*.frenpy)")
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as file:
                file.write(frenpy_template)
            self.console.append(f"Fichier .frenpy créé et enregistré: {save_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


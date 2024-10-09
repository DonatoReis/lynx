# settings_window.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QTextEdit, QMessageBox, QTabWidget, QWidget, QFileDialog,
    QColorDialog, QFormLayout
)
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QFont, QFontDatabase
import os

from config import load_config, save_config

class SettingsWindow(QDialog):
    config_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.setFixedSize(700, 600)

        # Load custom font
        self.load_custom_font()

        # Set default font
        app_font = QFont("Inter", 10)
        self.setFont(app_font)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Load existing configurations
        self.load_config()

        # Tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Tab Perguntas
        self.questions_tab = QWidget()
        self.questions_layout = QVBoxLayout()
        self.questions_tab.setLayout(self.questions_layout)
        self.tabs.addTab(self.questions_tab, "Perguntas")

        # Tab Prompts
        self.prompts_tab = QWidget()
        self.prompts_layout = QVBoxLayout()
        self.prompts_tab.setLayout(self.prompts_layout)
        self.tabs.addTab(self.prompts_tab, "Prompts")

        # Tab Configurações Gerais
        self.general_tab = QWidget()
        self.general_layout = QVBoxLayout()
        self.general_tab.setLayout(self.general_layout)
        self.tabs.addTab(self.general_tab, "Geral")

        # --- Configurações de Perguntas ---

        # Lista de perguntas
        self.questions_list = QListWidget()
        self.questions_list.addItems([q['question'] for q in self.questions])
        self.questions_list.currentRowChanged.connect(self.display_question_details)
        self.questions_layout.addWidget(self.questions_list)

        # Formulário de edição
        self.id_label = QLabel("ID:")
        self.id_input = QLineEdit()
        self.variable_label = QLabel("Nome da Variável:")
        self.variable_input = QLineEdit()
        self.question_label = QLabel("Pergunta:")
        self.question_input = QTextEdit()
        self.options_label = QLabel("Opções (separadas por vírgula):")
        self.options_input = QLineEdit()
        self.branching_label = QLabel("Ramificações (resposta: próximo_id):")
        self.branching_input = QTextEdit()
        self.branching_input.setPlaceholderText("Exemplo:\nSim: pergunta_3\nNão: pergunta_4\n\nUse uma linha por opção, no formato 'resposta: próximo_id'")

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.id_label)
        form_layout.addWidget(self.id_input)
        form_layout.addWidget(self.variable_label)
        form_layout.addWidget(self.variable_input)
        form_layout.addWidget(self.question_label)
        form_layout.addWidget(self.question_input)
        form_layout.addWidget(self.options_label)
        form_layout.addWidget(self.options_input)
        form_layout.addWidget(self.branching_label)
        form_layout.addWidget(self.branching_input)

        self.questions_layout.addLayout(form_layout)

        # Botões de ação
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Adicionar")
        self.add_button.clicked.connect(self.add_question)
        self.edit_button = QPushButton("Editar")
        self.edit_button.clicked.connect(self.edit_question)
        self.remove_button = QPushButton("Remover")
        self.remove_button.clicked.connect(self.remove_question)
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.remove_button)

        self.questions_layout.addLayout(buttons_layout)

        # --- Configurações de Prompts ---

        self.welcome_label = QLabel("Mensagem de Boas-Vindas:")
        self.welcome_input = QTextEdit()
        self.welcome_input.setText(self.prompts.get('welcome_message', ''))

        self.prompt_template_label = QLabel("Template do Prompt:")
        self.prompt_template_input = QTextEdit()

        # Define placeholder and behavior
        self.prompt_template_placeholder = """Exemplo de Template do Prompt:

Você é um especialista em {area}. Use as informações fornecidas para recomendar os melhores produtos. Variáveis disponíveis: {variavel1}, {variavel2}.

{informacoes_cliente}

# Produtos Disponíveis:
{produtos}

# Formato de Saída:
- Resumo das necessidades do cliente.
- Produto(s) recomendado(s).
- Justificativa para cada recomendação.
- Conselho ou métrica adicional relevante para a consulta do cliente.

# Notes:
- Utilize linguagem técnica adequada ao nível de conhecimento do cliente.
- Apresente a resposta de forma clara, coesa e fluida, evitando o uso de formatação com asteriscos ou marcadores.
"""
        if not self.prompts.get('prompt_template'):
            self.prompt_template_input.setText(self.prompt_template_placeholder)
            self.prompt_template_input.setStyleSheet("""
                QTextEdit {
                    color: gray;
                }
            """)
        else:
            self.prompt_template_input.setText(self.prompts.get('prompt_template', ''))

        # Apply stylesheet to hide scrollbar
        self.prompt_template_input.setStyleSheet("""
            QTextEdit {
                background-color: #2f2f2f;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Inter';
            }
            QTextEdit QScrollBar:vertical {
                background: transparent;
                width: 0px;
            }
            QTextEdit QScrollBar::handle:vertical {
                background: transparent;
                min-height: 0px;
            }
            QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
            QTextEdit QScrollBar::up-arrow:vertical, QTextEdit QScrollBar::down-arrow:vertical {
                background: none;
            }
            QTextEdit QScrollBar::add-page:vertical, QTextEdit QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Ensure scrolling is enabled
        self.prompt_template_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Connect focus events
        self.prompt_template_input.installEventFilter(self)

        self.system_message_label = QLabel("Mensagem do Sistema:")
        self.system_message_input = QTextEdit()
        self.system_message_input.setText(self.prompts.get('system_message', ''))
        self.system_message_input.setPlaceholderText("Exemplo: Você é um especialista em produtos químicos e tratamento de superfícies metálicas.")

        self.prompt_instructions_label = QLabel("Variáveis disponíveis: baseadas nas perguntas configuradas.")
        self.prompt_instructions_label.setStyleSheet("color: gray; font-style: italic;")

        prompts_form_layout = QVBoxLayout()
        prompts_form_layout.addWidget(self.welcome_label)
        prompts_form_layout.addWidget(self.welcome_input)
        prompts_form_layout.addWidget(self.prompt_template_label)
        prompts_form_layout.addWidget(self.prompt_template_input)
        prompts_form_layout.addWidget(self.system_message_label)
        prompts_form_layout.addWidget(self.system_message_input)
        prompts_form_layout.addWidget(self.prompt_instructions_label)

        self.prompts_layout.addLayout(prompts_form_layout)

        # --- Configurações Gerais ---

        self.api_key_label = QLabel("OpenAI API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setText(self.api_key)

        self.site_link_label = QLabel("Link do Site:")
        self.site_link_input = QLineEdit()
        self.site_link_input.setText(self.site_link)

        self.urls_label = QLabel("Arquivo de URLs:")
        self.urls_input = QLineEdit()
        self.urls_input.setText(self.urls_file)
        self.browse_button = QPushButton("Procurar")
        self.browse_button.clicked.connect(self.browse_urls_file)

        urls_layout = QHBoxLayout()
        urls_layout.addWidget(self.urls_input)
        urls_layout.addWidget(self.browse_button)

        urls_layout_widget = QWidget()
        urls_layout_widget.setLayout(urls_layout)

        # Option button color
        self.option_button_color_label = QLabel("Cor dos Botões de Opção:")
        self.option_button_color_button = QPushButton()
        self.option_button_color_button.setFixedSize(100, 30)
        self.option_button_color_button.clicked.connect(self.choose_option_button_color)
        self.option_button_color = self.config.get('option_button_color', '#2B4FFF')
        self.option_button_color_button.setStyleSheet(f"background-color: {self.option_button_color};")

        # Use QFormLayout for better organization
        general_form_layout = QFormLayout()
        general_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        general_form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        general_form_layout.setHorizontalSpacing(20)
        general_form_layout.setVerticalSpacing(10)

        # Fields and labels
        general_form_layout.addRow(self.api_key_label, self.api_key_input)
        general_form_layout.addRow(self.site_link_label, self.site_link_input)
        general_form_layout.addRow(self.urls_label, urls_layout_widget)
        general_form_layout.addRow(self.option_button_color_label, self.option_button_color_button)

        self.general_layout.addLayout(general_form_layout)

        # Save button
        self.save_button = QPushButton("Salvar Configurações")
        self.save_button.clicked.connect(self.save_config)
        self.layout.addWidget(self.save_button)

        # Styling
        self.apply_styles()

    def load_custom_font(self):
        font_paths = [
            os.path.join('fonts', 'Inter-Regular.ttf'),
            os.path.join('fonts', 'Inter-Bold.ttf'),
            os.path.join('fonts', 'Inter-Italic.ttf')
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                QFontDatabase.addApplicationFont(font_path)
            else:
                print(f"Font file not found: {font_path}")

    def apply_styles(self):
        input_style = """
            QTextEdit, QLineEdit {
                background-color: #2f2f2f;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Inter';
            }
            QLabel {
                color: white;
                font-family: 'Inter';
            }
            QListWidget {
                background-color: #2f2f2f;
                color: white;
                border: none;
                font-family: 'Inter';
            }
            QPushButton {
                background-color: #3A3A3A;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Inter';
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background-color: #2f2f2f;
                color: white;
                padding: 10px;
                margin-right: 5px;  /* Add spacing between tabs */
                border: none;
                border-radius: 5px;
                font-family: 'Inter';
            }
            QTabBar::tab:selected {
                background-color: #3A3A3A;
            }
            QTabBar::tab:hover {
                background-color: #4A4A4A;
            }
        """
        self.setStyleSheet(input_style)

    def load_config(self):
        config = load_config()
        self.questions = config.get('questions', [])
        self.prompts = config.get('prompts', {})
        self.api_key = config.get('api_key', '')
        self.site_link = config.get('site_link', '')
        self.urls_file = config.get('urls_file', '')
        self.config = config  # Store the full config

    def save_config(self):
        config = load_config()
        if 'prompts' not in config:
            config['prompts'] = {}

        config['questions'] = self.questions
        config['prompts']['welcome_message'] = self.welcome_input.toPlainText()

        # Handle prompt template placeholder
        prompt_template = self.prompt_template_input.toPlainText()
        if prompt_template == self.prompt_template_placeholder:
            prompt_template = ''
        config['prompts']['prompt_template'] = prompt_template

        config['prompts']['system_message'] = self.system_message_input.toPlainText()
        config['api_key'] = self.api_key_input.text()
        config['site_link'] = self.site_link_input.text()
        config['urls_file'] = self.urls_input.text()
        config['option_button_color'] = self.config.get('option_button_color', '#2B4FFF')

        save_config(config)
        QMessageBox.information(self, "Configurações", "Configurações salvas com sucesso.")
        self.config_saved.emit()

    def display_question_details(self, index):
        if index >= 0 and index < len(self.questions):
            question = self.questions[index]
            self.id_input.setText(question.get('id', ''))
            self.variable_input.setText(question.get('variable', ''))
            self.question_input.setText(question.get('question', ''))
            if question.get('options'):
                self.options_input.setText(', '.join(question['options']))
            else:
                self.options_input.clear()
            branching = question.get('branching', {})
            branching_text = "\n".join(f"{k}: {v}" for k, v in branching.items())
            self.branching_input.setText(branching_text)

    def parse_branching(self, text):
        branching = {}
        lines = text.strip().split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                branching[key.strip()] = value.strip()
            else:
                QMessageBox.warning(self, "Erro de Formatação", f"A linha '{line}' está no formato incorreto. Use 'resposta: próximo_id'.")
        return branching

    def add_question(self):
        new_question = {
            'id': self.id_input.text(),
            'variable': self.variable_input.text(),
            'question': self.question_input.toPlainText(),
            'options': [opt.strip() for opt in self.options_input.text().split(',')] if self.options_input.text() else None,
            'branching': self.parse_branching(self.branching_input.toPlainText())
        }
        self.questions.append(new_question)
        self.questions_list.addItem(new_question['question'])
        QMessageBox.information(self, "Configurações", "Pergunta adicionada com sucesso.")

    def edit_question(self):
        index = self.questions_list.currentRow()
        if index >= 0 and index < len(self.questions):
            self.questions[index] = {
                'id': self.id_input.text(),
                'variable': self.variable_input.text(),
                'question': self.question_input.toPlainText(),
                'options': [opt.strip() for opt in self.options_input.text().split(',')] if self.options_input.text() else None,
                'branching': self.parse_branching(self.branching_input.toPlainText())
            }
            self.questions_list.item(index).setText(self.question_input.toPlainText())
            QMessageBox.information(self, "Configurações", "Pergunta editada com sucesso.")

    def remove_question(self):
        index = self.questions_list.currentRow()
        if index >= 0 and index < len(self.questions):
            self.questions.pop(index)
            self.questions_list.takeItem(index)
            QMessageBox.information(self, "Configurações", "Pergunta removida com sucesso.")

    def browse_urls_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo de URLs", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            self.urls_input.setText(file_name)

    def choose_option_button_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.option_button_color_button.setStyleSheet(f"background-color: {color.name()};")
            self.config['option_button_color'] = color.name()

    def eventFilter(self, obj, event):
        if obj == self.prompt_template_input:
            if event.type() == QEvent.Type.FocusIn:
                if self.prompt_template_input.toPlainText() == self.prompt_template_placeholder:
                    self.prompt_template_input.clear()
                    self.prompt_template_input.setStyleSheet("""
                        QTextEdit {
                            background-color: #2f2f2f;
                            color: white;
                            border: none;
                            border-radius: 5px;
                            padding: 5px;
                            font-family: 'Inter';
                        }
                        QTextEdit QScrollBar:vertical {
                            background: transparent;
                            width: 0px;
                        }
                        QTextEdit QScrollBar::handle:vertical {
                            background: transparent;
                            min-height: 0px;
                        }
                        QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                            background: none;
                            height: 0px;
                        }
                        QTextEdit QScrollBar::up-arrow:vertical, QTextEdit QScrollBar::down-arrow:vertical {
                            background: none;
                        }
                        QTextEdit QScrollBar::add-page:vertical, QTextEdit QScrollBar::sub-page:vertical {
                            background: none;
                        }
                    """)
            elif event.type() == QEvent.Type.FocusOut:
                if not self.prompt_template_input.toPlainText().strip():
                    self.prompt_template_input.setText(self.prompt_template_placeholder)
                    self.prompt_template_input.setStyleSheet("""
                        QTextEdit {
                            background-color: #2f2f2f;
                            color: gray;
                            border: none;
                            border-radius: 5px;
                            padding: 5px;
                            font-family: 'Inter';
                        }
                        QTextEdit QScrollBar:vertical {
                            background: transparent;
                            width: 0px;
                        }
                        QTextEdit QScrollBar::handle:vertical {
                            background: transparent;
                            min-height: 0px;
                        }
                        QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                            background: none;
                            height: 0px;
                        }
                        QTextEdit QScrollBar::up-arrow:vertical, QTextEdit QScrollBar::down-arrow:vertical {
                            background: none;
                        }
                        QTextEdit QScrollBar::add-page:vertical, QTextEdit QScrollBar::sub-page:vertical {
                            background: none;
                        }
                    """)
        return super().eventFilter(obj, event)

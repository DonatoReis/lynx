# gui.py

import sys
import os
import unicodedata
import logging
import asyncio
import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton,
    QHBoxLayout, QLabel, QSizePolicy, QScrollArea,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QDialog, QFrame
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QFontDatabase, QPixmap, QAction, QColor

from config import load_config
from settings_window import SettingsWindow
import network
import cache as cache_module
import ai

import qasync

APP_VERSION = "1.0.0"

class CustomTextEdit(QTextEdit):
    enterPressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.enterPressed.emit()
        else:
            super().keyPressEvent(event)

class ChatGPTWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Carrega a fonte personalizada
        self.load_custom_font()

        self.message_labels = []

        # Carrega as configurações
        self.config = load_config()
        self.questions = self.config.get('questions', [])
        self.prompts = self.config.get('prompts', {})
        self.api_key = self.config.get('api_key', None)
        self.site_link = self.config.get('site_link', '')
        self.urls_file = self.config.get('urls_file', 'urls.txt')
        self.option_button_color = self.config.get('option_button_color', '#2B4FFF')

        # Configurações da janela principal
        self.setWindowTitle("Lynx")
        self.resize(800, 700)
        self.current_theme = 'dark'
        self.apply_theme()

        # Define o ícone da janela
        icon_path = os.path.join('imagens', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Layout principal
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        # Barra de menu
        self.menu_bar = QMenuBar(self)
        self.file_menu = QMenu("&Arquivo", self)
        self.settings_action = QAction("Configurações", self)
        self.settings_action.triggered.connect(self.open_settings_window)
        self.file_menu.addAction(self.settings_action)

        self.exit_action = QAction("Sair", self)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)
        self.menu_bar.addMenu(self.file_menu)

        self.help_menu = QMenu("&Ajuda", self)
        self.about_action = QAction("Sobre", self)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.help_menu.addAction(self.about_action)
        self.menu_bar.addMenu(self.help_menu)

        self.layout.setMenuBar(self.menu_bar)

        # Botão para alternar tema
        self.theme_toggle_button = QPushButton()
        self.theme_toggle_button.setFixedSize(30, 30)
        self.theme_toggle_button.setStyleSheet("border: none; margin-right: 10px;")
        self.theme_toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        self.update_theme_icon()

        # Adicionar o botão ao menu bar
        self.menu_bar.setCornerWidget(self.theme_toggle_button, Qt.Corner.TopRightCorner)

        # Área de rolagem para as mensagens
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)  # Remove a moldura
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none; /* Remove qualquer borda */
            }
            QScrollBar:vertical {
                width: 0px;
            }
            QScrollBar:horizontal {
                height: 0px;
            }
        """)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Widget que contém o display de mensagens
        self.chat_display_widget = QWidget(self)
        self.chat_display = QVBoxLayout(self.chat_display_widget)
        self.chat_display.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_display.setSpacing(10)
        self.chat_display_widget.setLayout(self.chat_display)
        self.chat_display_widget.setStyleSheet("background-color: transparent; padding: 10px;")
        self.chat_display_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scroll_area.setWidget(self.chat_display_widget)

        # Campo de entrada de texto
        self.text_input = CustomTextEdit(self)
        self.text_input.setPlaceholderText("Digite sua mensagem aqui...")
        self.text_input.setStyleSheet("""
            QTextEdit { 
                background-color: #2f2f2f;
                color: white;
                border-radius: 20px; 
                padding: 10px 20px;  
                font-size: 14px;
                border: none;
                font-family: 'Inter';
            }
            QTextEdit::vertical-scrollbar {
                width: 0px;
            }
            QTextEdit::horizontal-scrollbar {
                height: 0px;
            }
        """)
        self.text_input.setFont(QFont("Inter", 12))
        self.text_input.setFixedHeight(50)
        self.text_input.textChanged.connect(self.adjust_text_input_height)
        self.text_input.enterPressed.connect(self.send_message)

        # Botão de enviar
        self.send_button = QPushButton(self)
        send_icon_path = os.path.join('imagens', 'seta2.png')
        if os.path.exists(send_icon_path):
            pixmap = QPixmap(send_icon_path).scaled(24, 24)
            self.send_button.setIcon(QIcon(pixmap))
        else:
            self.send_button.setText("Enviar")
        self.send_button.setFixedSize(QSize(80, 40))
        self.send_button.setStyleSheet("""
            QPushButton { 
                background-color: #ffffff; 
                border: none; 
                border-radius: 20px; 
                color: black;
                font-family: 'Inter';
            }
            QPushButton:hover {
                background-color: #c1c1c1;
            }
            QPushButton:pressed {
                background-color: #b5b5b5;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
        """)
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)

        # Botão de limpar
        self.clear_button = QPushButton(self)
        clear_icon_path = os.path.join('imagens', 'clear.png')
        if os.path.exists(clear_icon_path):
            pixmap = QPixmap(clear_icon_path).scaled(24, 24)
            self.clear_button.setIcon(QIcon(pixmap))
        else:
            self.clear_button.setText("Limpar")
        self.clear_button.setFixedSize(QSize(80, 40))
        self.clear_button.setStyleSheet("""
            QPushButton { 
                background-color: #FF4F4F; 
                border: none; 
                border-radius: 20px; 
                color: white;
                font-family: 'Inter';
            }
            QPushButton:hover {
                background-color: #D13A3A;
            }
            QPushButton:pressed {
                background-color: #A32929;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
        """)
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_conversation)

        # Layout de entrada
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(10)
        self.text_input_container = QWidget()
        self.text_input_container.setLayout(QHBoxLayout())
        self.text_input_container.layout().setContentsMargins(0, 0, 0, 0)
        self.text_input_container.layout().setSpacing(10)
        self.text_input_container.layout().addWidget(self.text_input)
        self.text_input_container.layout().addWidget(self.send_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.text_input_container.layout().addWidget(self.clear_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        input_layout.addWidget(self.text_input_container)

        # Adiciona o scroll de mensagens e o input layout ao layout principal
        self.layout.addWidget(self.scroll_area, 1)
        self.layout.addLayout(input_layout)

        # Timer para animação de escrita
        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self.display_next_character)
        self.current_message = ""
        self.displayed_text = ""
        self.is_displaying = False
        self.is_user_message = False

        # Lista para manter referências aos QLabel e evitar coleta de lixo
        self.message_labels = []

        # Fonte personalizada para mensagens
        self.message_font = QFont("Inter", 12)
        self.user_message_font = QFont("Inter", 12)
        self.options_user = QFont("Inter", 10)

        # Estado da conversa
        self.conversa_ativa = False
        self.respostas_coletadas = {}
        self.current_question_index = 0

        # Inicializa a fila de mensagens
        self.message_queue = []

        # Inicia a conversa
        self.start_conversa()

        # Atalhos de teclado
        self.setup_shortcuts()

        # Verificar atualizações
        self.check_for_updates()

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
                print(f"Arquivo de fonte não encontrado: {font_path}")

    def apply_theme(self):
        if self.current_theme == 'dark':
            self.setStyleSheet(self.get_dark_theme_stylesheet())
        else:
            self.setStyleSheet(self.get_light_theme_stylesheet())
        
        # Atualizar o estilo das mensagens existentes
        for label in self.message_labels:
            is_user = label.property('is_user')
            label.setStyleSheet(self.get_message_style(is_user))

    def toggle_theme(self):
        if self.current_theme == 'dark':
            self.current_theme = 'light'
        else:
            self.current_theme = 'dark'
        self.apply_theme()
        self.update_theme_icon()

    def update_theme_icon(self):
        if self.current_theme == 'dark':
            icon_path = os.path.join('imagens', 'sun.png')  # Ícone do sol para tema claro
        else:
            icon_path = os.path.join('imagens', 'moon.png')  # Ícone da lua para tema escuro
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            self.theme_toggle_button.setIcon(QIcon(pixmap))
            self.theme_toggle_button.setIconSize(QSize(24, 24))
        else:
            self.theme_toggle_button.setText("Tema")

    def get_dark_theme_stylesheet(self):
        return """
            QWidget {
                background-color: #1e1e1e;
                color: white;
                font-family: 'Inter';
            }
            QLabel {
                color: white;
                font-family: 'Inter';
            }
            QPushButton {
                color: white;
                font-family: 'Inter';
            }
            QTextEdit {
                color: white;
                font-family: 'Inter';
            }
        """

    def get_light_theme_stylesheet(self):
        return """
            QWidget {
                background-color: #f0f0f0;
                color: black;
                font-family: 'Inter';
            }
            QLabel {
                color: black;
                font-family: 'Inter';
            }
            QPushButton {
                color: black;
                font-family: 'Inter';
            }
            QTextEdit {
                color: black;
                font-family: 'Inter';
            }
        """

    def setup_shortcuts(self):
        # Atalho para enviar mensagem (Ctrl+Enter)
        send_shortcut = QAction(self)
        send_shortcut.setShortcut(QKeySequence("Ctrl+Return"))
        send_shortcut.triggered.connect(self.send_message)
        self.addAction(send_shortcut)

        # Atalho para limpar conversa (Ctrl+L)
        clear_shortcut = QAction(self)
        clear_shortcut.setShortcut(QKeySequence("Ctrl+L"))
        clear_shortcut.triggered.connect(self.clear_conversation)
        self.addAction(clear_shortcut)

    def adjust_text_input_height(self):
        min_height = 50
        max_height = 150
        document = self.text_input.document()
        document.setTextWidth(self.text_input.viewport().width())
        height = document.size().height() + 20
        if height < min_height:
            height = min_height
        elif height > max_height:
            height = max_height
        self.text_input.setFixedHeight(int(height))

    def add_message(self, message, is_user, options=None, typing_interval=20):
        if self.is_displaying:
            self.message_queue.append((message, is_user, options, typing_interval))
            return

        self.current_message = message
        self.displayed_text = ""
        self.is_user_message = is_user
        self.is_displaying = True

        # Container de mensagem
        self.message_container = QHBoxLayout()
        self.message_container.setSizeConstraint(QHBoxLayout.SizeConstraint.SetMinimumSize)

        # Widget da mensagem
        self.message_widget = QWidget()
        self.message_layout = QVBoxLayout()
        self.message_layout.setContentsMargins(10, 10, 10, 10)
        self.message_widget.setLayout(self.message_layout)

        # QLabel para a mensagem
        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        self.message_label.setFont(self.user_message_font if is_user else self.message_font)
        self.message_label.setProperty('is_user', is_user)
        self.message_label.setStyleSheet(self.get_message_style(is_user))

        if is_user:
            max_width = int(self.width() * 0.7)
            self.message_label.setMaximumWidth(max_width)
            self.message_container.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            self.message_label.setMaximumWidth(self.width())
            self.message_container.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.message_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.message_layout.addWidget(self.message_label)

        # Botões de opções, se houver
        if not is_user and options:
            buttons_layout = QHBoxLayout()
            buttons_layout.setSpacing(10)
            for option in options:
                button = QPushButton(option)
                button.setFont(self.options_user)
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.option_button_color};
                        color: white;
                        border: none;
                        border-radius: 10px;
                        padding: 8px 12px;
                        font-family: 'Inter';
                    }}
                    QPushButton:hover {{
                        background-color: {self.darken_color(self.option_button_color, 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.darken_color(self.option_button_color, 40)};
                    }}
                """)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.clicked.connect(lambda checked, opt=option: self.option_selected(opt))
                buttons_layout.addWidget(button)
            self.message_layout.addLayout(buttons_layout)

        # Adicionar o widget da mensagem ao container
        self.message_container.addWidget(self.message_widget)

        # Adicionar o container de mensagem ao layout principal de chat
        self.chat_display.addLayout(self.message_container)

        # Manter referência ao QLabel para evitar coleta de lixo
        self.message_labels.append(self.message_label)

        # Iniciar a animação de digitação
        self.typing_index = 0
        self.typing_timer.start(typing_interval)

        # Rolagem automática para o final
        self.scroll_to_bottom()

    def darken_color(self, color_hex, amount):
        color = QColor(color_hex)
        h, s, v, a = color.getHsv()
        v = max(0, v - amount)
        color.setHsv(h, s, v, a)
        return color.name()

    def display_next_character(self):
        if self.typing_index < len(self.current_message):
            self.displayed_text += self.current_message[self.typing_index]
            if self.message_label:
                self.message_label.setText(self.displayed_text)
            self.typing_index += 1
            self.scroll_to_bottom()
        else:
            self.typing_timer.stop()
            self.is_displaying = False

            # Verifica se há mensagens na fila
            if self.message_queue:
                next_message, is_user, options, typing_interval = self.message_queue.pop(0)
                self.add_message(next_message, is_user, options, typing_interval)
            else:
                self.message_label = None  # Resetar a referência

    def option_selected(self, option):
        self.add_message(option, is_user=True)
        self.process_user_message(option)

    def get_message_style(self, is_user):
        if is_user:
            text_color = 'black' if self.current_theme == 'light' else 'white'
            background_color = '#e0e0e0' if self.current_theme == 'light' else '#424242'
            return f"""
                QLabel {{
                    background-color: {background_color};
                    color: {text_color};
                    border-radius: 15px;
                    padding: 10px;
                    margin: 5px;
                    font-family: 'Inter';
                    border: none;
                }}
            """
        else:
            text_color = 'black' if self.current_theme == 'light' else 'white'
            return f"""
                QLabel {{
                    color: {text_color};
                    background-color: transparent;
                    padding: 10px;
                    margin: 5px;
                    font-family: 'Inter';
                    border: none;
                }}
            """

    def send_message(self):
        user_text = self.text_input.toPlainText().strip()
        if user_text:
            self.add_message(user_text, is_user=True)
            self.text_input.clear()
            self.process_user_message(user_text)

    def process_user_message(self, message):
        if self.current_question_index < len(self.questions):
            current_question = self.questions[self.current_question_index]
            variable_name = current_question.get('variable', current_question['id'])
            self.respostas_coletadas[variable_name] = message

            # Obter o índice da próxima pergunta com base na ramificação
            next_question_index = self.get_next_question_index(current_question, message)
            self.current_question_index = next_question_index

            if self.current_question_index < len(self.questions):
                next_question = self.questions[self.current_question_index]
                self.add_message(next_question["question"], is_user=False, options=next_question.get("options"))
            else:
                # Iniciar processamento
                asyncio.create_task(self.start_processing())
        else:
            pass  # Conversa já terminou

    def get_next_question_index(self, current_question, message):
        branching = current_question.get('branching', {})
        # Normalizar a mensagem para correspondência
        normalized_message = message.strip().lower()
        # Verificar se a resposta corresponde a alguma opção de ramificação
        for key in branching:
            if key.strip().lower() == normalized_message:
                next_question_id = branching[key]
                # Encontrar o índice da próxima pergunta
                for index, question in enumerate(self.questions):
                    if question.get('id') == next_question_id:
                        return index
        # Caso contrário, ir para a próxima pergunta
        return self.current_question_index + 1

    def start_conversa(self):
        if self.conversa_ativa:
            return

        self.conversa_ativa = True
        self.respostas_coletadas = {}
        self.current_question_index = 0

        welcome_message = self.prompts.get("welcome_message", "Olá! Bem-vindo ao Lynx, sua solução de inteligência artificial personalizada! Estamos aqui para oferecer uma experiência moldada às suas necessidades, utilizando o poder do GPT-4o-mini. Conte conosco para adaptar cada funcionalidade e interagir de forma inteligente com seus projetos. Vamos começar a criar juntos!")
        self.add_message(welcome_message, is_user=False)

        if self.questions:
            first_question = self.questions[self.current_question_index]
            self.add_message(first_question["question"], is_user=False, options=first_question.get("options"))

    async def start_processing(self):
        self.add_loading_indicator()
        self.block_send(True)

        try:
            # Usar o arquivo de URLs definido nas configurações
            urls_file = self.urls_file if self.urls_file else 'urls.txt'
            urls = await network.ler_urls_arquivo(urls_file)
            cache = cache_module.carregar_cache()

            tasks = [network.extrair_conteudo(url, cache) for url in urls]
            results = await asyncio.gather(*tasks)
            todos_produtos = []
            for produtos in results:
                todos_produtos.extend(produtos)

            if todos_produtos:
                await ai.consultar_openai(
                    todos_produtos,
                    self.respostas_coletadas,
                    self.config,
                    callback=self.update_result_streaming
                )
            else:
                self.display_result("Nenhum produto encontrado nas URLs fornecidas.")
        except Exception as e:
            logging.error(f"Erro: {e}")
            self.display_error(str(e))

    def update_result_streaming(self, text):
        if not hasattr(self, 'streaming_label'):
            self.streaming_label = QLabel("", self)
            self.streaming_label.setWordWrap(True)
            self.streaming_label.setFont(self.message_font)
            self.streaming_label.setStyleSheet(self.get_message_style(False))
            self.chat_display.addWidget(self.streaming_label)
            self.scroll_to_bottom()
            # Manter referência para evitar coleta de lixo
            self.message_labels.append(self.streaming_label)
        self.streaming_label.setText(self.streaming_label.text() + text)
        self.scroll_to_bottom()

    def display_result(self, result):
        if hasattr(self, 'streaming_label'):
            self.chat_display.removeWidget(self.streaming_label)
            self.streaming_label.deleteLater()
            del self.streaming_label
        self.add_message(result, is_user=False)
        self.conversa_ativa = False
        self.block_send(False)

    def display_error(self, error):
        logging.error(f"Erro: {error}")
        self.add_message("Ocorreu um erro durante o processamento. Por favor, tente novamente.", is_user=False)
        self.conversa_ativa = False
        self.block_send(False)

    def normalize_string(self, s):
        return ''.join(
            c for c in unicodedata.normalize('NFD', s)
            if unicodedata.category(c) != 'Mn'
        ).lower()

    def scroll_to_bottom(self):
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_message_widths()

    def update_message_widths(self):
        max_width = int(self.width() * 0.7)
        for i in range(self.chat_display.count()):
            layout = self.chat_display.itemAt(i)
            if layout is not None:
                for j in range(layout.count()):
                    widget = layout.itemAt(j).widget()
                    if widget is not None:
                        label = widget.findChild(QLabel)
                        if label:
                            label.setMaximumWidth(max_width)

    def clear_conversation(self):
        self.clear_layout(self.chat_display)
        self.conversa_ativa = False
        self.respostas_coletadas = {}
        self.current_question_index = 0
        self.message_queue.clear()
        self.message_labels.clear()  # Limpar referências para evitar vazamento de memória
        self.start_conversa()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_layout(child.layout())

    def add_loading_indicator(self):
        self.loading_label = QLabel("Processando...", self)
        self.loading_label.setStyleSheet(self.get_message_style(False))
        self.chat_display.addWidget(self.loading_label)
        self.scroll_to_bottom()
        # Manter referência
        self.message_labels.append(self.loading_label)

    def remove_loading_indicator(self):
        if hasattr(self, 'loading_label'):
            self.chat_display.removeWidget(self.loading_label)
            self.loading_label.deleteLater()
            del self.loading_label

    def block_send(self, block):
        self.send_button.setEnabled(not block)
        self.text_input.setEnabled(not block)
        self.clear_button.setEnabled(not block)

    def open_settings_window(self):
        self.settings_window = SettingsWindow(self)
        self.settings_window.config_saved.connect(self.reload_config)
        self.settings_window.show()

    def reload_config(self):
        self.config = load_config()
        self.questions = self.config.get('questions', [])
        self.prompts = self.config.get('prompts', {})
        self.api_key = self.config.get('api_key', None)
        self.site_link = self.config.get('site_link', '')
        self.urls_file = self.config.get('urls_file', 'urls.txt')
        self.option_button_color = self.config.get('option_button_color', '#2B4FFF')
        # Reiniciar a conversa
        self.clear_conversation()

    def show_about_dialog(self):
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("Sobre")
        about_dialog.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        layout = QVBoxLayout()
        about_dialog.setLayout(layout)
        
        # Adicionar logotipo
        logo_path = os.path.join('imagens', 'logo.png')
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)

        version_label = QLabel(f"Versão {APP_VERSION}")
        version_label.setFont(QFont("Inter", 11))
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        # Descrição
        description_label = QLabel("Solução de inteligência artificial personalizada")
        description_label.setFont(QFont("Inter", 10))
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # Ajustar o tamanho da janela
        about_dialog.adjustSize()

        about_dialog.exec()

    def check_for_updates(self):
        try:
            response = requests.get("https://api.github.com/repos/yourusername/yourrepository/releases/latest")
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release['tag_name']
                if latest_version != APP_VERSION:
                    self.prompt_update(latest_version)
        except Exception as e:
            print(f"Erro ao verificar atualizações: {e}")

    def prompt_update(self, latest_version):
        reply = QMessageBox.question(
            self,
            "Atualização Disponível",
            f"Uma nova versão ({latest_version}) está disponível. Deseja atualizar agora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.download_and_install_update()

    def download_and_install_update(self):
        try:
            update_url = "https://github.com/yourusername/yourrepository/releases/latest/download/yourapp_installer.exe"
            response = requests.get(update_url)
            with open("update_installer.exe", "wb") as f:
                f.write(response.content)
            os.startfile("update_installer.exe")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao atualizar: {e}")

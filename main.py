# main.py

import sys
import logging
from PyQt6.QtWidgets import QApplication
from gui import ChatGPTWindow
import os
from dotenv import load_dotenv
import qasync
import asyncio

# Carrega variáveis de ambiente
load_dotenv()

# Configura o logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

async def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = ChatGPTWindow()
    window.show()
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    asyncio.run(main())

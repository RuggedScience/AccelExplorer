import logging
from logging.handlers import RotatingFileHandler

from app import run

handler = RotatingFileHandler("AccelExplorer.log", maxBytes=100_000_000, backupCount=2)
logging.basicConfig(level=logging.WARN, handlers=[handler])

run()

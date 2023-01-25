import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler("AccelExplorer.log", backupCount=2)
logging.basicConfig(level=logging.WARN, handlers=[handler, logging.StreamHandler()])

if __name__ == "__main__":
    import sys
    from app import run

    sys.exit(run())

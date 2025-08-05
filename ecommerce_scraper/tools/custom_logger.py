import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """
    Formats log records into a JSON string.
    """
    def format(self, record):
        """
        Formats a log record into a JSON object with date, type, and message.
        """
        log_record = {
            "date": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "type": record.levelname,
            "message": record.getMessage()
        }
        return json.dumps(log_record)

def setup_logger(name, log_file='app.log.json'):
    """
    Sets up a logger that writes logs in JSON format to a specified file.

    Args:
        name (str): The name of the logger.
        log_file (str): The file to write logs to.

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent adding duplicate handlers if the logger is already configured.
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a file handler to write to the log file.
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger

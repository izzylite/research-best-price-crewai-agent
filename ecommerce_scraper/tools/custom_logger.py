import logging
import json
import os
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

def setup_logger(name, log_dir='logs'):
    """
    Sets up a logger that writes logs in JSON format to a specified file.

    Args:
        name (str): The name of the logger.
        log_dir (str): The directory to write logs to.

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent adding duplicate handlers if the logger is already configured.
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create the log directory if it doesn't exist.
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create a unique log file name with a timestamp.
    log_file = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.log.json'
    log_path = os.path.join(log_dir, log_file)

    # Create a file handler to write to the log file.
    handler = logging.FileHandler(log_path, mode='a')
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger

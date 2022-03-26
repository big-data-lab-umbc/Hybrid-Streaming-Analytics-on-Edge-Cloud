import logging
import os
import sys

# Set all the constants
TIMEOUT = 10

# Intialize all the variables with default values
UPDATED_CONFIG = False
SCHEDULED_THREAD = None
DEFAULT_INTERVAL_SECS = 60

# Get a logger
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

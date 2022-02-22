import logging
import os
import sys

from awsiot.greengrasscoreipc.model import QOS

# Set all the constants
QOS_TYPE = QOS.AT_LEAST_ONCE
TIMEOUT = 30

# Intialize all the variables with default values
UPDATED_CONFIG = False
TOPIC = "edge-to-cloud/metadata"

# Get a logger
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

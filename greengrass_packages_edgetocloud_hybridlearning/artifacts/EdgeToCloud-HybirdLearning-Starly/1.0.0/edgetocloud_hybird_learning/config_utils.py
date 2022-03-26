import logging
import os
import sys

from awsiot.greengrasscoreipc.model import QOS

# Set all the constants
SCORE_THRESHOLD = 0.3
MAX_NO_OF_RESULTS = 5
SHAPE = (224, 224)
QOS_TYPE = QOS.AT_LEAST_ONCE
TIMEOUT = 30
SCORE_CONVERTER = 255

# Intialize all the variables with default values
CAMERA = None
DEFAULT_PREDICTION_INTERVAL_SECS = 3600
DEFAULT_USE_CAMERA = "false"
UPDATED_CONFIG = False
SCHEDULED_THREAD = None
TOPIC = "edge-to-cloud/lstm_hybrid_learning"
METADATA_TOPIC = "edge-to-cloud/metadata"

# Get a logger
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Get the model directory and images directory from the env variables.
MODEL_DIR = os.path.expandvars(os.environ.get("TFLITE_IC_MODEL_DIR"))

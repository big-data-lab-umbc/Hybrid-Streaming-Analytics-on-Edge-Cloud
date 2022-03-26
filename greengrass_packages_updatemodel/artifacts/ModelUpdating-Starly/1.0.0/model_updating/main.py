import time
import threading
import boto3
import os

import config_utils
import IPCUtils as ipc_utils

AWS_ACCESS_KEY_ID="AKIASHT77xxxxxxxxxx"
AWS_SECRET_ACCESS_KEY="36E3p9vvc1TtscMVxxxxxxxxxx"

s3_client = boto3.client('s3',aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
s3 = boto3.resource('s3',aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
bucket_model ='edge-to-cloud-streaming-model'

def sync_from_s3():
    get_last_modified = lambda obj: int(obj['LastModified'].strftime('%s'))

    while True:
        objs = s3_client.list_objects_v2(Bucket=bucket_model)['Contents']
        last_added = [obj['Key'] for obj in sorted(objs, key=get_last_modified)][-1]  
        if ".tflite" in last_added:
            break

    os.remove('/home/pi/Downloads/greengrass_packages_edgetocloud_hybridlearning/artifacts/EdgeToCloud-HybirdLearning-Starly/1.0.0/edgetocloud_hybird_learning/sample_model/Ot_stream.tflite')
    s3.Bucket(bucket_model).download_file(last_added, '/home/pi/Downloads/greengrass_packages_edgetocloud_hybridlearning/artifacts/EdgeToCloud-HybirdLearning-Starly/1.0.0/edgetocloud_hybird_learning/sample_model/Ot_stream.tflite')
    
    config_utils.logger.info("Update streaming model successful.")

def set_configuration(config):
    new_config = {}
    new_config["interval_secs"] = config_utils.DEFAULT_INTERVAL_SECS
    config_utils.logger.warning(
        "Using default update interval: {}".format(
            config_utils.DEFAULT_INTERVAL_SECS
        )
    )

    run_update(new_config, True)


def run_update(new_config, config_changed):
    """
    Uses the new config to run inference.

    :param new_config: Updated config if the config changed. Else, the last updated config.
    :param config_changed: Is True when run_update is called after setting the newly updated config.
    Is False if run_update is called using scheduled thread as the config hasn't changed.
    """

    if config_changed:
        if config_utils.SCHEDULED_THREAD is not None:
            config_utils.SCHEDULED_THREAD.cancel()
        config_changed = False

    sync_from_s3()

    config_utils.SCHEDULED_THREAD = threading.Timer(
        int(new_config["interval_secs"]), run_update, [new_config, config_changed]
    )
    config_utils.SCHEDULED_THREAD.start()

set_configuration(ipc_utils.IPCUtils().get_configuration())
ipc_utils.IPCUtils().get_config_updates()

while True:
    if config_utils.UPDATED_CONFIG:
        set_configuration(ipc_utils.IPCUtils().get_configuration())
        config_utils.UPDATED_CONFIG = False
    time.sleep(1)

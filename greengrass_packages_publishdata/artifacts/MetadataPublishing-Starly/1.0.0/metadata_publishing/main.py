import time
import sys
import os
import json
import pandas as pd

import config_utils
import IPCUtils as ipc_utils


def DataPublishing(METADATA):        
        print('Now sending METADATA to AWS Iot')
        try:
            #config_utils.logger.info(json.dumps(PAYLOAD))
            if config_utils.TOPIC != "":
                ipc_utils.IPCUtils().publish_metadata_to_cloud(METADATA)
            else:
                config_utils.logger.info("No topic set to publish the inference results to the cloud.")
        except Exception as e:
            config_utils.logger.error("Exception occured during prediction: {}".format(e))
        


source_data = '/home/pi/Downloads/greengrass_packages_publishdata/artifacts/MetadataPublishing-Starly/1.0.0/metadata_publishing/sample_data/temperature_stream.csv'
# with open(source_data) as json_file:
#     metadata = json.load(json_file)

metadata = pd.read_csv(source_data, header=None, index_col=0, squeeze=True).to_dict()
DataPublishing(metadata)

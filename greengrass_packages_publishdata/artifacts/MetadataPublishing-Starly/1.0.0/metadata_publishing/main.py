import time
import sys
import os
import json
import pandas as pd

from pyspark.sql import SparkSession
import pyspark.sql.functions as F
import pyspark.sql.types as tp

import config_utils
import IPCUtils as ipc_utils

spark_version = '3.0.3'
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages org.apache.spark:spark-sql-kafka-0-10_2.12:{}'.format(spark_version)

#def DataPublishing(METADATA):
def DataPublishing(df, epoch_id):    
    split_col = F.split(df.value, ',')
    # df = df.withColumn('TimeStamp', F.to_timestamp(F.regexp_replace(split_col.getItem(0), '"', ''),
    #                                                'yyyy-mm-dd HH:mm:ss.SSS'))
    df = df.withColumn('Date_time', F.regexp_replace(split_col.getItem(0), '"', '').cast(tp.TimestampType()))
    df = df.withColumn('Db1t_avg', split_col.getItem(1).cast(tp.DoubleType()))
    df = df.withColumn('Db2t_avg', split_col.getItem(2).cast(tp.DoubleType()))
    df = df.withColumn('Gb1t_avg', split_col.getItem(3).cast(tp.DoubleType()))
    df = df.withColumn('Gb2t_avg', split_col.getItem(4).cast(tp.DoubleType()))
    df = df.withColumn('Ot_avg', F.regexp_replace(split_col.getItem(5), '"', '').cast(tp.DoubleType()))
    
    #df = df.dropna()
    df = df.drop('value')

    dfw = df.select('Date_time','Db1t_avg', 'Db2t_avg','Gb1t_avg', 'Gb2t_avg', 'Ot_avg')
    dfw.show(5)

    dfw = dfw.withColumn('Date_time', dfw.Date_time.cast(tp.StringType()))
    METADATA = dfw.toPandas().to_dict('dict')

    print('Now sending batch %s of METADATA to AWS Iot'%str(epoch_id))
    try:
        #config_utils.logger.info(json.dumps(PAYLOAD))
        if config_utils.TOPIC != "":
            ipc_utils.IPCUtils().publish_metadata_to_cloud(METADATA)
        else:
            config_utils.logger.info("No topic set to publish the inference results to the cloud.")
    except Exception as e:
        config_utils.logger.error("Exception occured during prediction: {}".format(e))
        


# source_data = '/home/pi/Downloads/greengrass_packages_publishdata/artifacts/MetadataPublishing-Starly/1.0.0/metadata_publishing/sample_data/temperature_stream.csv'
# # with open(source_data) as json_file:
# #     metadata = json.load(json_file)

# metadata = pd.read_csv(source_data, header=None, index_col=0, squeeze=True).to_dict()

#DataPublishing(metadata)
broker = "localhost:9092"
source_topic = "batch_input_topic"
batch_size = '60 seconds'

spark = SparkSession \
    .builder \
    .appName("PublishingData") \
    .getOrCreate()

lines = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", broker) \
    .option("startingOffsets", "earliest") \
    .option("subscribe", source_topic) \
    .load()

spark.sparkContext.setLogLevel("FATAL")

query = lines.writeStream.trigger(processingTime=batch_size).foreachBatch(DataPublishing).start()
query.awaitTermination()
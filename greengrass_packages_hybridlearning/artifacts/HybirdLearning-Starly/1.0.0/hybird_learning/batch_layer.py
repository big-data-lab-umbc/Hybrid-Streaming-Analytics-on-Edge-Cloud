from __future__ import print_function
from pyspark.sql import SparkSession
from fitModel import lstm
import time
import pyspark.sql.functions as F
from pyspark.sql.functions import lag, col, lit
import pyspark.sql.types as tp
import sys
import os
import json

import config_utils
import IPCUtils as ipc_utils

from subprocess import check_output, Popen, call, PIPE, STDOUT
#from keras import backend as K
#os.environ['PYSPARK_SUBMIT_ARGS'] = "--packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.3 pyspark-shell"
#os.environ['PYSPARK_PYTHON'] = "./environment/bin/python3"

def recordstream(df, model_path):
    start_time = time.time()
    '''
    split_col = F.split(df.value, ',')
    # df = df.withColumn('TimeStamp', F.to_timestamp(F.regexp_replace(split_col.getItem(0), '"', ''),
    #                                                'yyyy-mm-dd HH:mm:ss.SSS'))
    df = df.withColumn('Date_time', F.regexp_replace(split_col.getItem(0), '"', '').cast(tp.TimestampType()))
    df = df.withColumn('Db1t_avg', split_col.getItem(1).cast(tp.DoubleType()))
    df = df.withColumn('Db2t_avg', split_col.getItem(2).cast(tp.DoubleType()))
    df = df.withColumn('Gb1t_avg', split_col.getItem(3).cast(tp.DoubleType()))
    df = df.withColumn('Gb2t_avg', split_col.getItem(4).cast(tp.DoubleType()))
    df = df.withColumn('Ot_avg', F.regexp_replace(split_col.getItem(5), '"', '').cast(tp.DoubleType()))
    df = df.drop('value')
    '''

    # df = df.dropna()
    # df = df.withColumn('Date_time', df.Date_time.cast(tp.TimestampType()))
    # df = df.withColumn('Db1t_avg', df.Db1t_avg.cast(tp.DoubleType()))
    # df = df.withColumn('Db2t_avg', df.Db2t_avg.cast(tp.DoubleType()))
    # df = df.withColumn('Gb1t_avg', df.Db1t_avg.cast(tp.DoubleType()))
    # df = df.withColumn('Gb2t_avg', df.Db2t_avg.cast(tp.DoubleType()))
    # df = df.withColumn('Ot_avg', df.Db1t_avg.cast(tp.DoubleType()))

    dfp = df.select('Date_time','Db1t_avg', 'Db2t_avg','Gb1t_avg', 'Gb2t_avg', 'Ot_avg')
    dfp.show(5)

    if len(dfp.take(1)) != 0:
        df_final,lrModels = lstm(2,dfp,model_path)

        #K.clear_session()
        end_time = time.time()
        df_final = df_final.withColumn('Latency_Start', lit(start_time))
        df_final = df_final.withColumn('Latency_End', lit(end_time))
        df_final = df_final.withColumn('Latency', lit(end_time-start_time))
        # df_final = df_final.withColumn('value',(F.concat(col("TS"),lit(","),
        #                                     col("Temp"),lit(","),
        #                                     col("Temp_Predict"),lit(","),
        #                                     col("RMSE_Score"),lit(","),
        #                                     col("Latency_Start"),lit(","),
        #                                     col("Latency_End"),lit(","),
        #                                     col("Latency")
        #                                     )).cast(tp.StringType()))
        df_final.show(5)

        '''
        #prepare PAYLOAD
        PAYLOAD = df_final.select('value').toPandas().to_dict('dict')

        #prepare METADATA
        meta_final = df.select('Date_time','Db1t_avg', 'Db2t_avg','Gb1t_avg', 'Gb2t_avg', 'Ot_avg')
        meta_final = meta_final.withColumn('Date_time', meta_final.Date_time.cast(tp.StringType()))
        #meta_final['Date_time'] = meta_final['Date_time'].astype(str)
        METADATA = meta_final.toPandas().to_dict('dict')

        print('Now sending PAYLOAD and METADATA to AWS Iot')
        try:
            #config_utils.logger.info(json.dumps(PAYLOAD))
            if config_utils.TOPIC != "" and config_utils.METADATA_TOPIC != "":
                ipc_utils.IPCUtils().publish_results_to_cloud(PAYLOAD)
                ipc_utils.IPCUtils().publish_metadata_to_cloud(METADATA)
            else:
                config_utils.logger.info("No topic set to publish the inference results to the cloud.")
        except Exception as e:
            config_utils.logger.error("Exception occured during prediction: {}".format(e))
        '''
        return df_final.select('TS','Temp','Temp_Predict','RMSE_Score','MAE_Score','MSE_Score','Latency')


# if len(sys.argv) != 3:
#     print("Usage: spark-submit xx.py <data csv file path> <model folder path>", file=sys.stderr)
#     sys.exit(-1)

# source_data = str(sys.argv[1])  #'./sample_data/temperature_stream.csv'
# #batch_size = str(sys.argv[2]) + ' seconds'
# g_model = str(sys.argv[2])  #'./sample_model/Ot_avg.tflite'


def run_batch():
    source_data = '/home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_data/temperature_stream.csv'
    g_model = '/home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model/Ot_avg.tflite'

    # spark = SparkSession.builder.config("spark.archives","pyspark_venv.tar.gz#environment").appName("Lstm_BatchLayer").enableHiveSupport().getOrCreate()

    # lines = spark \
    #     .readStream \
    #     .format("kafka") \
    #     .option("kafka.bootstrap.servers", broker) \
    #     .option("startingOffsets", "earliest") \
    #     .option("subscribe", source_topic) \
    #     .load()
    # spark.sparkContext.setLogLevel("FATAL")
    # query = lines.writeStream.trigger(processingTime=batch_size).foreachBatch(recordstream).start()
    # query.awaitTermination()

    spark = SparkSession \
        .builder \
        .appName("BatchLayer") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("FATAL")

    dataFrame = spark.read.csv(source_data, header=True, inferSchema=True)
    
    return recordstream(dataFrame,g_model)

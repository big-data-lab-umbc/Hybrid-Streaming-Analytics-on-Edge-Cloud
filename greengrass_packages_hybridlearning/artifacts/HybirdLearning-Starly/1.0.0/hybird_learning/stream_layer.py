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

def predict(df, model_path):
    start_time = time.time()
    
    dfw = df.select('Date_time','Db1t_avg', 'Db2t_avg','Gb1t_avg', 'Gb2t_avg', 'Ot_avg')
    dfw.show(5)
    
    if len(dfw.take(1)) != 0:
        df_final,lrModels = lstm(2,dfw,model_path)

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

        return df_final.select('TS','Temp','Temp_Predict','RMSE_Score','MAE_Score','MSE_Score','Latency')


def run_speed():
    source_data = '/home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_data/temperature_stream.csv'
    g_model = '/home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model/Ot_stream.tflite'

    spark = SparkSession \
        .builder \
        .appName("StreamingLayer") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("FATAL")

    dataFrame = spark.read.csv(source_data, header=True, inferSchema=True)
    
    return predict(dataFrame,g_model)

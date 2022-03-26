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

spark_version = '3.0.3'
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages org.apache.spark:spark-sql-kafka-0-10_2.12:{}'.format(spark_version)

#from subprocess import check_output, Popen, call, PIPE, STDOUT

def predict(df, epoch_id):
    start_time = time.time()
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
    
    if len(dfw.take(1)) != 0:
        df_final,lrModels = lstm(2,dfw,g_model)

        end_time = time.time()
        df_final = df_final.withColumn('Latency_Start', lit(start_time))
        df_final = df_final.withColumn('Latency_End', lit(end_time))
        df_final = df_final.withColumn('Latency', lit(end_time-start_time))
        df_final = df_final.withColumn('value',(F.concat(col("TS"),lit(","),
                                            col("Temp"),lit(","),
                                            col("Temp_Predict"),lit(","),
                                            col("RMSE_Score"),lit(","),
                                            col("MAE_Score"),lit(","),
                                            col("MSE_Score"),lit(","),
                                            col("Latency_Start"),lit(","),
                                            col("Latency_End"),lit(","),
                                            col("Latency")
                                            )).cast(tp.StringType()))
        #df_final.show(5)
        ds = df_final.select('value')

        print('Now sending Message on Kafka topic',sink_topic)
        ds.selectExpr("CAST(value AS STRING)")\
            .write\
            .format("kafka")\
            .option("kafka.bootstrap.servers", broker)\
            .option("topic", sink_topic)\
            .save()

        #return df_final.select('TS','Temp','Temp_Predict','RMSE_Score','MAE_Score','MSE_Score','Latency')


# def run_speed():
#source_data = '/home/pi/Downloads/greengrass_packages_edgetocloud_hybridlearning/artifacts/EdgeToCloud-HybirdLearning-Starly/1.0.0/edgetocloud_hybird_learning/sample_data/temperature_stream.csv'
g_model = '/home/pi/Downloads/greengrass_packages_edgetocloud_hybridlearning/artifacts/EdgeToCloud-HybirdLearning-Starly/1.0.0/edgetocloud_hybird_learning/sample_model/Ot_stream.tflite'

broker = sys.argv[1]
source_topic = sys.argv[2]
sink_topic = sys.argv[3]
batch_size = str(sys.argv[4]) + ' seconds'

spark = SparkSession \
    .builder \
    .appName("StreamingLayer") \
    .getOrCreate()

lines = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", broker) \
    .option("startingOffsets", "earliest") \
    .option("subscribe", source_topic) \
    .load()

spark.sparkContext.setLogLevel("FATAL")

query = lines.writeStream.trigger(processingTime=batch_size).foreachBatch(predict).start()
query.awaitTermination()

# dataFrame = spark.read.csv(source_data, header=True, inferSchema=True)

# return predict(dataFrame,g_model)

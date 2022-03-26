from __future__ import print_function
from pyspark.sql import SparkSession
import time
import pyspark.sql.functions as F
from pyspark.sql.functions import lag, col, lit
import pyspark.sql.types as tp
import sys
import os
import json

import config_utils
import IPCUtils as ipc_utils
from fitModel import lstm

from subprocess import check_output, Popen, call, PIPE, STDOUT
from sklearn.metrics import mean_squared_error,mean_absolute_error
from sklearn.metrics import log_loss
from scipy.optimize import minimize

spark_version = '3.0.3'
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages org.apache.spark:spark-sql-kafka-0-10_2.12:{}'.format(spark_version)

### finding the optimum weights (https://www.kaggle.com/starlywang/finding-ensemble-weights)
# TODO: change to right arguments
def get_best_weights(Batch_model_path,Speed_model_path,epoch_id):

    ensumble_models = []
    ensumble_predictions = []

    ensumble_models.append(load_model(Speed_model_path+'modelOt_avg'+'{}'.format(str(epoch_id))+".json", Speed_model_path+'weightsOt_avg'+'{}'.format(str(epoch_id))+".npy"))
    ensumble_models.append(load_model(Batch_model_path+"modelOt_avg.json",Batch_model_path+"weightsOt_avg.npy"))

    for ensumble_model in ensumble_models:
        ensumble_predictions.append(ensumble_model.predict(test_x))

    def log_loss_func(weights):
        ''' scipy minimize will pass the weights as a numpy array '''
        final_prediction = 0
        for weight, prediction in zip(weights, predictions):
                final_prediction += weight*prediction

        return log_loss(test_y, final_prediction)
    
    #the algorithms need a starting value, right not we chose 0.5 for all weights
    #its better to choose many random starting points and run minimize a few times
    starting_values = [0.5]*len(ensumble_predictions)

    #adding constraints and a different solver
    cons = ({'type':'eq','fun':lambda w: 1-sum(w)})
    #weights are bound between 0 and 1
    bounds = [(0,1)]*len(ensumble_predictions)

    res = minimize(log_loss_func, starting_values, method='SLSQP', bounds=bounds, constraints=cons)

    print('Ensamble Score: {best_score}'.format(best_score=res['fun']))
    print('Best Weights: {weights}'.format(weights=res['x']))

    return res['x']

def weighted_predict(df, epoch_id):
    start_time = time.time()
    #sp_df = stream_result.select('TS','Temp','Temp_Predict','RMSE_Score','Latency') #also have 'MAE_Score','MSE_Score'
    #bt_df = batch_result.select('TS','Temp','Temp_Predict','RMSE_Score','Latency')

    split_col = F.split(df.value, ',')
    # df = df.withColumn('TimeStamp', F.to_timestamp(F.regexp_replace(split_col.getItem(0), '"', ''),
    #                                                'yyyy-mm-dd HH:mm:ss.SSS'))
    df = df.withColumn('TimeStamp', F.regexp_replace(split_col.getItem(0), '"', '').cast(tp.TimestampType()))
    df = df.withColumn('Temp', split_col.getItem(1).cast(tp.DoubleType()))
    df = df.withColumn('Temp_Predict', split_col.getItem(2).cast(tp.DoubleType()))
    df = df.withColumn('RMSE_Score', split_col.getItem(3).cast(tp.DoubleType()))    
    df = df.withColumn('MAE_Score', split_col.getItem(4).cast(tp.DoubleType()))   
    df = df.withColumn('MSE_Score', split_col.getItem(5).cast(tp.DoubleType())) 
    df = df.withColumn('Latency_Start', split_col.getItem(6).cast(tp.DoubleType()))
    df = df.withColumn('Latency_End', split_col.getItem(7).cast(tp.DoubleType()))
    df = df.withColumn('Latency', F.regexp_replace(split_col.getItem(8), '"', '').cast(tp.DoubleType()))
    df = df.drop('value')

    sp_df = df.select('TimeStamp','Temp','Temp_Predict','RMSE_Score','MAE_Score','Latency_Start','Latency_End','Latency')\
        .where("topic='{}'".format(str(sp_topic))).dropDuplicates(['TimeStamp'])
    bt_df = df.select('TimeStamp','Temp','Temp_Predict','RMSE_Score','MAE_Score','Latency_Start','Latency_End','Latency')\
        .where("topic='{}'".format(str(ba_topic))).dropDuplicates(['TimeStamp'])

    #ensumble_best_weights = get_best_weights()  #list[speed:batch]
    df_final = (
        sp_df.alias('sp').join(bt_df.alias('bt'), on=sp_df['TimeStamp'] == bt_df['TimeStamp'],
                                    how='inner').selectExpr('sp.TimeStamp as TS',
                                                            'sp.Latency as Speed_Latency',
                                                            'bt.Latency as Batch_Latency',
                                                            'sp.Latency_Start as Speed_Latency_Start',
                                                            'bt.Latency_Start as Batch_Latency_Start',
                                                            'sp.Latency_End as Speed_Latency_End',
                                                            'bt.Latency_End as Batch_Latency_End',
                                                            'round(sp.Temp,3) as RT_Temp',
                                                            'round(sp.Temp_Predict,3) as Speed_RT_Temp',
                                                            'round(bt.Temp_Predict,3) as Batch_RT_Temp',
                                                            'round(({}*sp.Temp_Predict + {}*bt.Temp_Predict),3) as Wt_Temp'.format(str(s_wt),str(b_wt)),
                                                            'round(sp.RMSE_Score,3) as Speed_RMSE',
                                                            'round(bt.RMSE_Score,3) as Batch_RMSE',
                                                            'round(sp.MAE_Score,3) as Speed_MAE',
                                                            'round(bt.MAE_Score,3) as Batch_MAE'
                                                            )
                )
    df_final.dropDuplicates(['TS'])

    weighted_predictions = [row[0] for row in df_final.select('Wt_Temp').collect()]
    actual_value = [row[0] for row in df_final.select('RT_Temp').collect()]

    if len(weighted_predictions) != 0:
        wt_rmse = mean_squared_error(actual_value, weighted_predictions, squared=False)
        wt_mae = mean_absolute_error(actual_value, weighted_predictions)
    else:
        wt_rmse = 0
        wt_mae = 0

    df_final = df_final.withColumn("Wt_RMSE", lit(wt_rmse))
    df_final = df_final.withColumn("Wt_MAE", lit(wt_mae))
    end_time = time.time()

    df_final = df_final.withColumn('Wt_Latency', lit(end_time-start_time))

    df_final.show(5)
    df_final_pd = df_final.toPandas().dropna().sort_values(by=['TS']).drop_duplicates(subset=['TS'], keep='first')
    record_num = str(df_final_pd.shape[0])
    print("Number of records: ",record_num)

    try:
        df_final_pd.to_csv("/home/pi/Downloads/Output-HybirdResults/Output-HybirdResults-%s.csv"%epoch_id,index=False)
    except:
        print("Please create directory ~/Downloads/Output-HybirdResults.")

    # #prepare PAYLOAD
    # df_final = df_final.withColumn('TS', df_final.TS.cast(tp.StringType()))
    # PAYLOAD = df_final.toPandas().to_dict('dict')
    # print('Now sending batch %s of PAYLOAD to AWS Iot'%str(epoch_id))
    # try:
    #     #config_utils.logger.info(json.dumps(PAYLOAD))
    #     if config_utils.TOPIC != "":
    #         ipc_utils.IPCUtils().publish_results_to_cloud(PAYLOAD)
    #     else:
    #         config_utils.logger.info("No topic set to publish the hybrid inference results to the cloud.")
    # except Exception as e:
    #     config_utils.logger.error("Exception occured during prediction: {}".format(e))

    try:
        speed_latency = df_final_pd['Speed_Latency'].values[0]
        batch_latency = df_final_pd['Batch_Latency'].values[0]
        speed_RMSE = df_final_pd['Speed_RMSE'].values[0]
        batch_RMSE = df_final_pd['Batch_RMSE'].values[0]
        speed_MAE = df_final_pd['Speed_MAE'].values[0]
        batch_MAE = df_final_pd['Batch_MAE'].values[0]
        
        PAYLOAD = {}
        PAYLOAD["Epoch_Id"] = str(epoch_id)
        PAYLOAD["Record_Num"] = record_num

        PAYLOAD["Speed_Latency"] = str(speed_latency)
        PAYLOAD["Batch_Latency"] = str(batch_latency)
        PAYLOAD["Wt_Latency"] = str(end_time-start_time)

        PAYLOAD["Speed_RMSE"] = str(speed_RMSE)
        PAYLOAD["Batch_RMSE"] = str(batch_RMSE)
        PAYLOAD["Wt_RMSE"] = str(wt_rmse)

        PAYLOAD["Speed_MAE"] = str(speed_MAE)
        PAYLOAD["Batch_MAE"] = str(batch_MAE)
        PAYLOAD["Wt_MAE"] = str(wt_mae)

        PAYLOAD["MQTT_Publish_Time"] = str(time.time())

        print('Now sending batch %s of PAYLOAD to AWS Iot'%str(epoch_id))
        try:
            #config_utils.logger.info(json.dumps(PAYLOAD))
            if config_utils.TOPIC != "":
                ipc_utils.IPCUtils().publish_results_to_cloud(PAYLOAD)
            else:
                config_utils.logger.info("No topic set to publish the hybrid inference results to the cloud.")
        except Exception as e:
            config_utils.logger.error("Exception occured during prediction: {}".format(e))
    except:
        pass


s_wt = "0.3" #speed layer weight
b_wt = "0.7"

broker = sys.argv[1]
sp_topic = sys.argv[2]
ba_topic = sys.argv[3]
batch_size = str(sys.argv[4]) + ' seconds'
# batch_result = run_batch() #dataframe
# stream_result = run_speed()

spark = SparkSession \
    .builder \
    .appName("HybridLayer") \
    .getOrCreate()

predictions = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", broker) \
    .option("startingOffsets", "earliest") \
    .option("subscribe", str(sp_topic)+','+str(ba_topic)) \
    .load()

spark.sparkContext.setLogLevel("FATAL")
query = predictions.writeStream.trigger(processingTime=batch_size).foreachBatch(weighted_predict).start()
query.awaitTermination()
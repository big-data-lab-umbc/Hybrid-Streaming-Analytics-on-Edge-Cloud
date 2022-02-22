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
from batch_layer import run_batch
from stream_layer import run_speed

from subprocess import check_output, Popen, call, PIPE, STDOUT
from sklearn.metrics import mean_squared_error
from sklearn.metrics import log_loss
from scipy.optimize import minimize


### finding the optimum weights
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



s_wt = "0.6" #speed layer weight
b_wt = "0.4"

batch_result = run_batch() #dataframe
stream_result = run_speed()

spark = SparkSession \
    .builder \
    .appName("HybridLayer") \
    .getOrCreate()
spark.sparkContext.setLogLevel("FATAL")

start_time = time.time()
sp_df = stream_result.select('TS','Temp','Temp_Predict','RMSE_Score','Latency') #also have 'MAE_Score','MSE_Score'
bt_df = batch_result.select('TS','Temp','Temp_Predict','RMSE_Score','Latency')

#ensumble_best_weights = get_best_weights()  #list[speed:batch]
df_final = (
    sp_df.alias('sp').join(bt_df.alias('bt'), on=sp_df['TS'] == bt_df['TS'],
                                how='inner').selectExpr('sp.TS as TimeStamp',
                                                        'sp.Latency as Speed_Latency',
                                                        'bt.Latency as Batch_Latency',
                                                        'round(sp.Temp,3) as RT_Temp',
                                                        'round(sp.Temp_Predict,3) as Speed_RT_Temp',
                                                        'round(bt.Temp_Predict,3) as Batch_RT_Temp',
                                                        'round(({}*sp.Temp_Predict + {}*bt.Temp_Predict),3) as Wt_Temp'.format(str(s_wt),str(b_wt)),
                                                        'round(sp.RMSE_Score,3) as Speed_RMSE',
                                                        'round(bt.RMSE_Score,3) as Batch_RMSE'
                                                        )
            )

weighted_predictions = [row[0] for row in df_final.select('Wt_Temp').collect()]
actual_value = [row[0] for row in df_final.select('RT_Temp').collect()]

if len(weighted_predictions) != 0:
    wt_rmse = mean_squared_error(actual_value, weighted_predictions, squared=False)
else:
    wt_rmse = 0

df_final = df_final.withColumn("Wt_RMSE", lit(wt_rmse))
end_time = time.time()

df_final = df_final.withColumn('Wt_Latency', lit(end_time-start_time))
#df_final = df_final.withColumn('Total_Latency', col("Speed_Latency")+col("Batch_Latency")+col("Wt_Latency"))

df_final.show(5)

#prepare PAYLOAD
df_final = df_final.withColumn('TimeStamp', df_final.TimeStamp.cast(tp.StringType()))
PAYLOAD = df_final.toPandas().to_dict('dict')
print('Now sending PAYLOAD to AWS Iot')
try:
    #config_utils.logger.info(json.dumps(PAYLOAD))
    if config_utils.TOPIC != "":
        ipc_utils.IPCUtils().publish_results_to_cloud(PAYLOAD)
    else:
        config_utils.logger.info("No topic set to publish the hybrid inference results to the cloud.")
except Exception as e:
    config_utils.logger.error("Exception occured during prediction: {}".format(e))

from __future__ import print_function
from pyspark.sql import SparkSession
from pyspark.sql.functions import lag, col
from pyspark.sql.functions import monotonically_increasing_id
from pyspark.sql.functions import lit
from pyspark.sql.window import Window
from pyspark.ml.regression import LinearRegression
from pyspark.ml.feature import VectorAssembler
from pyspark.ml import Pipeline
from pyspark.ml import PipelineModel
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql.types import *
from pyspark.sql import types as T
from pyspark.sql.functions import udf
from pyspark.sql import functions as F
from pyspark.ml import Transformer
from pyspark.ml.param.shared import HasInputCol, HasOutputCol
from pyspark.ml.feature import MinMaxScaler
from datetime import datetime
import numpy as np
import pandas as pd
import json
import sys
import os
import time
#from keras.models import model_from_json
#from keras import backend as K

spark = SparkSession \
    .builder \
    .appName("BatchLayer") \
    .getOrCreate()
spark.sparkContext.setLogLevel("FATAL")


np_load_old = np.load

# modify the default parameters of np.load
np.load = lambda *a,**k: np_load_old(*a, allow_pickle=True, **k)


def load_model(model_path, weights_path):
    """
    Load model.
    """
    with open(model_path, 'r') as f:
        data = json.load(f)

    model = model_from_json(data)
    weights = np.load(weights_path)
    model.set_weights(weights)

    return model

def prepare_collected_data(data):
    list_features = []
    list_labels = []
    for i in range(len(data)):
        list_features.append(np.asarray(data[i][0]))
        list_labels.append(data[i][1])
    return np.asarray(list_features), np.asarray(list_labels)

def prepare_collected_data_test(data):
    list_features = []
    for i in range(len(data)):
        list_features.append(np.asarray(data[i][0]))
    return np.asarray(list_features)


def lstm(p_lag, dataFrame, model_path):
    # print(p_lag)
    current_lag = p_lag

    # df_len_ori: number of variables in model, K
    x_list = dataFrame.columns
    # print('x_list',x_list)
    df_len_ori = len(x_list)
    # print("df_len_ori is ")
    # print(df_len_ori)
    dataFrame_names = dataFrame.columns
    # dataFrame = dataFrame.withColumn("id", monotonically_increasing_id())
    # dataFrame.printSchema()
    # dataFrame.show(10)
    # Here, VAR model regression_type is "const" same to R VAR library, and the default in Python VAR library
    # w = Window().partitionBy().orderBy(col("id"))
    w = Window().partitionBy().orderBy(col("Date_time"))
    df_len = len(dataFrame.columns)
    ys_lagged_list = ["const"]
    # Making sure first column is not considered for forecasting
    for i in range(1, p_lag + 1):
        for j in range(0, df_len):
            # making sure index column is not considered as feature column
            if x_list[j] != 'Date_time':
                ys_lagged_list.append("%st-%s" % (x_list[j], str(i)))
                # print('2',ys_lagged_list)
                dataFrame = dataFrame.withColumn("%st-%s" % (x_list[j], str(i)), lag(dataFrame[j], i, 0).over(w))
                # print('3')
    # print("Showing DataFrame")
    # dataFrame.show(5)
    # print('ys_lagged_list',ys_lagged_list)

    # add "const" column of value 1 to get intercept when fitting the regression model
    dataFrame = dataFrame.withColumn("const", lit(1))
    dataFrame = dataFrame.withColumn("const", lag("const", p_lag, 0).over(w))
    dataFrame = dataFrame.withColumn("rid", monotonically_increasing_id())
    dataFrame = dataFrame.filter(dataFrame.rid >= p_lag)
    # dataFrame.show(5)
    #     build ys_lagged dataframe, will be used in F-test
    ys_lagged = dataFrame.select(ys_lagged_list)
    ys_lagged_len = ys_lagged.count()
    # print('ye dikhai lagged value')
    # ys_lagged.show(10)

    #     dataFrame = dataFrame.drop('id')
    dataFrame = dataFrame.drop('rid')
    dataFrame = dataFrame.drop('const')
    input_feature_name = dataFrame.schema.names

    # input_feature_name.remove("id")
    for x_name in x_list:
        input_feature_name.remove('{}'.format(x_name))

    print("input_feature_name",input_feature_name)

    train_dataFrame, validation_dataFrame = dataFrame.randomSplit([0.8,0.2], seed=1)

    va =  VectorAssembler(inputCols=input_feature_name,outputCol="features")
    #scaler = MinMaxScaler(inputCol="features", outputCol="scaledFeatures")

    #pipeline = Pipeline(stages=[va, scaler])
    pipeline = Pipeline(stages=[va])
    pipiline_model = pipeline.fit(dataFrame)

    train_transformed = pipiline_model.transform(train_dataFrame)
    validation_transformed = pipiline_model.transform(validation_dataFrame)

    # Temp_train_x, Temp_train_y = prepare_collected_data(train_transformed.select('scaledFeatures', 'Ot_avg').collect())
    # Temp_validation_x, Temp_validation_y = prepare_collected_data(validation_transformed.select('scaledFeatures', 'Ot_avg').collect())
    Temp_train_x, Temp_train_y = prepare_collected_data(train_transformed.select('features', 'Ot_avg').collect())
    Temp_validation_x, Temp_validation_y = prepare_collected_data(validation_transformed.select('features', 'Ot_avg').collect())

    Temp_train_x = Temp_train_x.reshape((Temp_train_x.shape[0], 1, Temp_train_x.shape[1]))
    Temp_validation_x = Temp_validation_x.reshape((Temp_validation_x.shape[0], 1, Temp_validation_x.shape[1]))
    print("@@@@",Temp_train_x.shape)

    n_label = 1

    # hyperparameters
    epochs = 50
    batch = 64
    lr = 0.001

    evaluator = RegressionEvaluator()
    models = {}
    lrModels=[]

    test_transformed = pipiline_model.transform(dataFrame)
    #test = prepare_collected_data_test(test_transformed.select('scaledFeatures').collect())
    test = prepare_collected_data_test(test_transformed.select('features').collect())
    test = test.reshape((test.shape[0], 1, test.shape[1])).astype('float32')
    true_value = test_transformed.select('Ot_avg').collect()

    import tflite_runtime.interpreter as tflite
    try:
        interpreter = tflite.Interpreter(model_path=model_path)
    except:
        time.sleep(3)
        interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    predictions=[]
    for i in range(test.shape[0]):
        interpreter.set_tensor(input_details[0]["index"], test[i:i+1, :, :])
        interpreter.invoke()
        p = interpreter.get_tensor(output_details[0]["index"])
        predictions.append(p)

    temp_df = test_transformed.select("Date_time",'Ot_avg')

    predictions = np.array(predictions).reshape((test.shape[0], 1))
    df = pd.DataFrame(true_value, columns=['Ot_avg'])
    df['prediction'] = predictions
    df_predictions = spark.createDataFrame(df)

    evaluator.setLabelCol("{}".format('Ot_avg'))
    evaluator.setMetricName('rmse')
    evaluator.setPredictionCol("prediction")
    rmse = evaluator.evaluate(df_predictions)

    evaluator.setMetricName('mse')
    mse = evaluator.evaluate(df_predictions)

    evaluator.setMetricName('mae')
    mae = evaluator.evaluate(df_predictions)

    #models['Ot_avg'] = model

    df_predictions2 = df_predictions.join(temp_df,['Ot_avg'])

    df_final = df_predictions2.selectExpr('Date_time as TS','Ot_avg as Temp','prediction as Temp_Predict')
    df_final = df_final.withColumn("MAE_Score", lit(mae))
    df_final = df_final.withColumn("MSE_Score", lit(mse))
    df_final = df_final.withColumn("RMSE_Score", lit(rmse))
    lrModels.append('{}'.format('Ot_avg'))

    #df_final.show(5)
    return df_final,lrModels

###
# tensorflow == 2.2.0
# Use historical data to train a lstm model, then save the model to local. Used on big data cluster.
###
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
import tensorflow as tf
import json
import sys
import os

os.environ['PYSPARK_PYTHON'] = "../../environment/bin/python3"

spark = SparkSession.builder \
    .config("spark.archives","../../pyspark_venv.tar.gz#environment") \
    .appName("SparkLstmTraining") \
    .getOrCreate()
spark.sparkContext.setLogLevel("FATAL")

get_weekday = udf(lambda x: x.weekday())

class DateConverter(Transformer):
    def __init__(self, inputCol, outputCol):
        self.inputCol = inputCol
        self.outputCol = outputCol
    
    def check_input_type(self, schema):
        field = schema[self.inputCol]
        if (field.dataType != TimestampType()):
            raise Exception('Input type %s did not match input type TimestampType' % field.dataType)

    def _transform(self, df):
        self.check_input_type(df.schema)
        return df.withColumn(self.outputCol, df.date.cast(self.inputCol))
    
class DayExtractor(Transformer):
    def __init__(self, inputCol, outputCol='day'):
        self.inputCol = inputCol
        self.outputCol = outputCol
    
    def check_input_type(self, schema):
        field = schema[self.inputCol]
        if (field.dataType != DateType()):
            raise Exception('DayExtractor input type %s did not match input type DateType' % field.dataType)

    def _transform(self, df):
        self.check_input_type(df.schema)
        return df.withColumn(self.outputCol, F.dayofmonth(df[self.inputCol]))
    
class MonthExtractor(Transformer):
    def __init__(self, inputCol, outputCol='month'):
        self.inputCol = inputCol
        self.outputCol = outputCol
    
    def check_input_type(self, schema):
        field = schema[self.inputCol]
        if (field.dataType != DateType()):
            raise Exception('MonthExtractor input type %s did not match input type DateType' % field.dataType)

    def _transform(self, df):
        self.check_input_type(df.schema)
        return df.withColumn(self.outputCol, F.month(df[self.inputCol]))
    
class YearExtractor(Transformer):
    def __init__(self, inputCol, outputCol='year'):
        self.inputCol = inputCol
        self.outputCol = outputCol
    
    def check_input_type(self, schema):
        field = schema[self.inputCol]
        if (field.dataType != DateType()):
            raise Exception('YearExtractor input type %s did not match input type DateType' % field.dataType)

    def _transform(self, df):
        self.check_input_type(df.schema)
        return df.withColumn(self.outputCol, F.year(df[self.inputCol]))
    
    
class WeekDayExtractor(Transformer):
    def __init__(self, inputCol, outputCol='weekday'):
        self.inputCol = inputCol
        self.outputCol = outputCol
    
    def check_input_type(self, schema):
        field = schema[self.inputCol]
        if (field.dataType != DateType()):
            raise Exception('WeekDayExtractor input type %s did not match input type DateType' % field.dataType)

    def _transform(self, df):
        self.check_input_type(df.schema)
        return df.withColumn(self.outputCol, get_weekday(df[self.inputCol]).cast('int'))
    
    
class WeekendExtractor(Transformer):
    def __init__(self, inputCol='weekday', outputCol='weekend'):
        self.inputCol = inputCol
        self.outputCol = outputCol
    
    def check_input_type(self, schema):
        field = schema[self.inputCol]
        if (field.dataType != IntegerType()):
            raise Exception('WeekendExtractor input type %s did not match input type IntegerType' % field.dataType)

    def _transform(self, df):
        self.check_input_type(df.schema)
        return df.withColumn(self.outputCol, F.when(((df[self.inputCol] == 5) | (df[self.inputCol] == 6)), 1).otherwise(0))
    
    
class SerieMaker(Transformer):
    def __init__(self, inputCol='scaledFeatures', outputCol='serie', dateCol='Date_time', serieSize=7):
        self.inputCol = inputCol
        self.outputCol = outputCol
        self.dateCol = dateCol
        self.serieSize = serieSize

    def _transform(self, df):
        window = Window.partitionBy().orderBy(self.dateCol)
        series = []   
        
        df = df.withColumn('filled_serie', F.lit(0))
        
        for index in reversed(range(0, self.serieSize)):
            window2 = Window.partitionBy().orderBy(self.dateCol).rowsBetween((7 - index), 7)
            col_name = (self.outputCol + '%s' % index)
            series.append(col_name)
            df = df.withColumn(col_name, F.when(F.isnull(F.lag(F.col(self.inputCol), index).over(window)), F.first(F.col(self.inputCol), ignorenulls=True).over(window2)).otherwise(F.lag(F.col(self.inputCol), index).over(window)))
            df = df.withColumn('filled_serie', F.when(F.isnull(F.lag(F.col(self.inputCol), index).over(window)), (F.col('filled_serie') + 1)).otherwise(F.col('filled_serie')))

        df = df.withColumn('rank', F.rank().over(window))
        df = df.withColumn(self.outputCol, F.array(*series))
        
        return df.drop(*series)


class MonthBeginExtractor(Transformer):
    def __init__(self, inputCol='day', outputCol='monthbegin'):
        self.inputCol = inputCol
        self.outputCol = outputCol
    
    def check_input_type(self, schema):
        field = schema[self.inputCol]
        if (field.dataType != IntegerType()):
            raise Exception('MonthBeginExtractor input type %s did not match input type IntegerType' % field.dataType)

    def _transform(self, df):
        self.check_input_type(df.schema)
        return df.withColumn(self.outputCol, F.when((df[self.inputCol] <= 7), 1).otherwise(0))
    
    
class MonthEndExtractor(Transformer):
    def __init__(self, inputCol='day', outputCol='monthend'):
        self.inputCol = inputCol
        self.outputCol = outputCol
    
    def check_input_type(self, schema):
        field = schema[self.inputCol]
        if (field.dataType != IntegerType()):
            raise Exception('MonthEndExtractor input type %s did not match input type IntegerType' % field.dataType)

    def _transform(self, df):
        self.check_input_type(df.schema)
        return df.withColumn(self.outputCol, F.when((df[self.inputCol] >= 24), 1).otherwise(0))
    
    
class YearQuarterExtractor(Transformer):
    def __init__(self, inputCol='month', outputCol='yearquarter'):
        self.inputCol = inputCol
        self.outputCol = outputCol
    
    def check_input_type(self, schema):
        field = schema[self.inputCol]
        if (field.dataType != IntegerType()):
            raise Exception('YearQuarterExtractor input type %s did not match input type IntegerType' % field.dataType)

    def _transform(self, df):
        self.check_input_type(df.schema)
        return df.withColumn(self.outputCol, F.when((df[self.inputCol] <= 3), 0)
                            .otherwise(F.when((df[self.inputCol] <= 6), 1)
                            .otherwise(F.when((df[self.inputCol] <= 9), 2)
                            .otherwise(3))))

def prepare_data(data):
    list_result = []
    for i in range(len(data)):
        list_result.append(np.asarray(data[i]))
    return np.asarray(list_result)

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

def save_model(model_path, weights_path, model):
    """
    Save model.
    """
    np.save(weights_path, model.get_weights())
    with open(model_path+".json", 'w') as f:
        json.dump(model.to_json(), f)

def pre_lstm(dataFrame, model_path, weights_path):
    
    #from keras import optimizers
    #from keras.models import Sequential
    #from keras.layers import Dense, LSTM, Dropout, GRU
    from tensorflow.keras import datasets, layers, models

    import pandas as pd
    import json
    #from keras.models import model_from_json

    p_lag = 2
    current_lag = p_lag

    # df_len_ori: number of variables in model, K
    x_list = dataFrame.columns
    # print('x_list',x_list)
    df_len_ori = len(x_list)
    # print("df_len_ori is ")
    # print(df_len_ori)
    dataFrame_names = dataFrame.columns
    dataFrame = dataFrame.withColumn("id", monotonically_increasing_id())
    # dataFrame.printSchema()
    # dataFrame.show(10)
    # Here, VAR model regression_type is "const" same to R VAR library, and the default in Python VAR library
    # w = Window().partitionBy().orderBy(col("id"))
    w = Window().partitionBy().orderBy(col("id"))
    df_len = len(dataFrame.columns)
    ys_lagged_list = ["const"]
    # Making sure first column is not considered for forecasting
    for i in range(1, p_lag + 1):
        for j in range(0, df_len - 1):
            # making sure index column is not considered as feature column
            if x_list[j] != 'Date_time':
                ys_lagged_list.append("%st-%s" % (x_list[j], str(i)))
                print('2',ys_lagged_list)
                dataFrame = dataFrame.withColumn("%st-%s" % (x_list[j], str(i)), lag(dataFrame[j], i, 0).over(w))
                # print('3')
    # print("Showing DataFrame")
    dataFrame.show(5)
    print('ys_lagged_list',ys_lagged_list)

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

    dataFrame = dataFrame.drop('id')
    dataFrame = dataFrame.drop('rid')
    dataFrame = dataFrame.drop('const')
    input_feature_name = dataFrame.schema.names

    # input_feature_name.remove("id")
    for x_name in x_list:
        input_feature_name.remove('{}'.format(x_name))

    print("input_feature_name",input_feature_name)

    train_dataFrame, validation_dataFrame = dataFrame.randomSplit([0.8,0.2], seed=1)

    # Feature extraction
    dc = DateConverter(inputCol='Date_time', outputCol='dateFormated')
    dex = DayExtractor(inputCol='dateFormated')
    mex = MonthExtractor(inputCol='dateFormated')
    yex = YearExtractor(inputCol='dateFormated')
    # wdex = WeekDayExtractor(inputCol='dateFormated')
    # wex = WeekendExtractor()
    # mbex = MonthBeginExtractor()
    # meex = MonthEndExtractor()
    # yqex = YearQuarterExtractor()

    # Data process
    #va =  VectorAssembler(inputCols=["Db1t_avg","Db2t_avg","Gb1t_avg","Gb2t_avg"],outputCol="features")
    va =  VectorAssembler(inputCols=input_feature_name,outputCol="features")
    scaler = MinMaxScaler(inputCol="features", outputCol="scaledFeatures")

    # Serialize data
    sm = SerieMaker(inputCol='scaledFeatures', dateCol='Date_time', serieSize=len(dataFrame.columns))

    # pipeline = Pipeline(stages=[va, scaler, sm])
    # pipiline_model = pipeline.fit(train_dataFrame)
    #pipeline = Pipeline(stages=[va, scaler])
    pipeline = Pipeline(stages=[va])
    pipiline_model = pipeline.fit(dataFrame)

    train_transformed = pipiline_model.transform(train_dataFrame)
    validation_transformed = pipiline_model.transform(validation_dataFrame)

    # Temp_train_x, Temp_train_y = prepare_collected_data(train_transformed.select('scaledFeatures', 'Ot_avg').collect())
    # Temp_validation_x, Temp_validation_y = prepare_collected_data(validation_transformed.select('scaledFeatures', 'Ot_avg').collect())
    Temp_train_x, Temp_train_y = prepare_collected_data(train_transformed.select('features', 'Ot_avg').collect())
    Temp_validation_x, Temp_validation_y = prepare_collected_data(validation_transformed.select('features', 'Ot_avg').collect())
    print(Temp_train_x.shape,Temp_train_y.shape,Temp_train_x[0,:],Temp_train_y[0])

    # reshape input to be 3D [samples, timesteps, features]
    Temp_train_x = Temp_train_x.reshape((Temp_train_x.shape[0], 1, Temp_train_x.shape[1]))
    Temp_validation_x = Temp_validation_x.reshape((Temp_validation_x.shape[0], 1, Temp_validation_x.shape[1]))

    n_label = 1

    # hyperparameters
    epochs = 50
    batch = 512
    lr = 0.001

    evaluator = RegressionEvaluator()
    models = {}
    lrModels = []
    lstem_predictions = {}
    for select_y in x_list:
        if select_y == 'Ot_avg':
            model_key = '{}'.format(select_y)

            # design network
            model = tf.keras.Sequential()
            model.add(tf.keras.layers.LSTM(40, input_shape=(Temp_train_x.shape[1],Temp_train_x.shape[2])))
            model.add(tf.keras.layers.Dense(10, kernel_initializer='glorot_normal', activation='relu'))
            model.add(tf.keras.layers.Dense(n_label))
            model.summary()

            model.compile(loss='mae', optimizer='Adam', metrics=['mse', 'msle'])

            history = model.fit(Temp_train_x, Temp_train_y, epochs=epochs, batch_size=batch, validation_data=(Temp_validation_x, Temp_validation_y), verbose=2, shuffle=False)
            #ids = RTvalidation_y
            # predictions = model.predict(Temp_validation_x)
            
            lrModels.append('{}'.format(select_y))
            models[model_key] = model

            #save_model(model_path, weights_path, model)
            predictions = model.predict(Temp_validation_x)
            print(predictions)
    return lrModels, models

if __name__ == "__main__":

    data_file_name = './sample_data/train.csv'
    model_path = './'
    weights_path = './weights'
    dataFrame = spark.read.csv(data_file_name, header=True, inferSchema=True)
    lr_model = []
    models = {}
    lr_model, models = pre_lstm(dataFrame, model_path, weights_path)
    # saving trained model for each endogenous variable
    for i in range(0,len(lr_model)):
        print('lr_model',lr_model[i])
        trained_model = models[lr_model[i]]
        ##trained_model.write().overwrite().save(model_path+'{}'.format(str(lr_model[i])))
        
        #np.save(weights_path+'{}'.format(str(lr_model[i])), trained_model.get_weights())
        #with open(model_path+'{}'.format(str(lr_model[i]))+".json", 'w') as f:
        #    json.dump(trained_model.to_json(), f)
    
        trained_model.save(model_path+'{}'.format(str(lr_model[i]))+".h5")

        new_model= tf.keras.models.load_model(filepath=model_path+'{}'.format(str(lr_model[i]))+".h5")
        converter = tf.lite.TFLiteConverter.from_keras_model(new_model)
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS, tf.lite.OpsSet.SELECT_TF_OPS]
        tflite_model = converter.convert()
        open(model_path+'{}'.format(str(lr_model[i]))+".tflite", "wb").write(tflite_model)



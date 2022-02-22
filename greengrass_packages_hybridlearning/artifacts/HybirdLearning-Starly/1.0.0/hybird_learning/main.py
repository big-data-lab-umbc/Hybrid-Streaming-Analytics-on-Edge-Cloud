import sys
import os
import json
import time

from subprocess import check_output, Popen, call, PIPE, STDOUT


epoch = 0
while True:
    try:
        call('mv /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model/Ot_stream.tflite /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model_archived/',shell=True)
        call('mv /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model_archived/Ot_stream.tflite /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model_archived/Ot_stream_%s.tflite'%epoch,shell=True)
        
        #call('rm /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model/Ot_avg.tflite',shell=True)
        call('mv /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model/Ot_avg.tflite /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model_archived/',shell=True)
        call('mv /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model_archived/Ot_avg.tflite /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model_archived/Ot_avg_%s.tflite'%epoch,shell=True)
    except:
        pass

    try:
        #TODO: the wget file should be different with the file in last loop.
        call('wget -P /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model/ https://kddworkshop.s3.us-west-2.amazonaws.com/Ot_stream.tflite',shell=True)
        epoch+=1
    except:
        time.sleep(10)
        continue

    call('wget -P /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model/ https://kddworkshop.s3.us-west-2.amazonaws.com/Ot_avg.tflite',shell=True)
    call('sudo /greengrass/v2/bin/greengrass-cli component restart  --names "HybirdLearning-Starly"',shell=True)
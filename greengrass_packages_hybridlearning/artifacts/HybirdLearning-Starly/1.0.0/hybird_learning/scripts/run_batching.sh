#!/bin/sh

set -e

wget -P /home/pi/Downloads/greengrass_packages_hybridlearning/artifacts/HybirdLearning-Starly/1.0.0/hybird_learning/sample_model/ https://kddworkshop.s3.us-west-2.amazonaws.com/Ot_avg.tflite

python3 {artifacts:path}/hybird_learning/batch_layer.py
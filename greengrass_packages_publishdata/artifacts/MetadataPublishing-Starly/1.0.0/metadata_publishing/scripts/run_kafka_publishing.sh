#!/bin/sh

set -e

python3 /home/pi/Downloads/hybird_learning/sample_data/kafkapublish.py localhost:9092 batch_input_topic /home/pi/Downloads/hybird_learning/sample_data/temperature_train.csv 2500
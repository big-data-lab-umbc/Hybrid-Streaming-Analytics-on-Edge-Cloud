# An Edge-Cloud Integrated Framework for Flexible and Dynamic Stream Analytics
With the popularity of Internet of Things (IoT), edge computing and cloud computing, more and more stream analytics applications are being developed including real-time trend prediction and object detection on top of IoT sensing data. One popular type of stream analytics is the recurrent neural network (RNN) deep learning model based time series or sequence data prediction and forecasting. Different from traditional analytics that assumes data to be processed are available ahead of time and will not change, stream analytics deals with data that are being generated continuously and data trend/distribution could change (aka concept drift), which will cause prediction/forecasting accuracy to drop over time. One other challenge is to find the best resource provisioning for stream analytics to achieve good overall latency.
In this paper, we study how to best leverage edge and cloud resources to achieve better accuracy and latency for RNN-based stream analytics. We propose a novel edge-cloud integrated framework for hybrid stream analytics that support low latency inference on the edge and high capacity training on the cloud. We study the flexible deployment of our hybrid learning framework, namely edge-centric, cloud-centric and edge-cloud integrated. Further, our hybrid learning framework can dynamically combine inference results from an RNN model pre-trained based on historical data and another RNN model re-trained periodically based on the most recent data. Using real-world and simulated stream datasets, our experiments show the proposed edge-cloud deployment is the best among all three deployment types in terms of latency. For accuracy, the experiments show our dynamic learning approach performs the best among all learning approaches for all three concept drift scenarios. 

## Edge-cloud integrated deployment in AWS IoT

### Prerequirement in RPi

We use Debian11 (Bullseye) in RPi4 with Python3.8.

```bash
sudo apt-get install libopenjp2-7 libilmbase23 libopenexr-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libgtk-3-0 libwebp-dev
sudo python3 -m pip install opencv-python
sudo python3 -m pip install tflite-runtime==2.5.0
sudo python3 -m pip install awsiotsdk

sudo python3 -m pip install pandas
sudo python3 -m pip install scikit-learn scipy

sudo python3 -m pip install
wget https://dlcdn.apache.org/spark/spark-3.0.3/spark-3.0.3-bin-hadoop2.7.tgz
tar xvf spark-*
sudo mv spark-3.0.3-bin-hadoop2.7 spark
echo "PATH=/home/pi/spark/bin:/home/pi/spark/sbin:$PATH" >> ~/.profile
echo "PYSPARK_PYTHON=/usr/bin/python3" >> ~/.profile
echo "PYSPARK_DRIVER_PYTHON=/usr/bin/python3" >> ~/.profile
echo "SPARK_HOME=/home/pi/spark" >> ~/.profile
source ~/.profile

sudo python3 -m pip install kafka-python
wget https://dlcdn.apache.org/kafka/3.1.0/kafka_2.13-3.1.0.tgz
tar -xzf kafka_2.13-3.1.0.tgz
echo "PATH=/home/pi/kafka_2.13-3.1.0/bin:$PATH" >> ~/.profile
source ~/.profile
```

1. For speed layer model training, we need more powerful machine like the EC2 instance. We need to initial a c5.4xlarge EC2 instance in our example. Then copy [install_depandencies.sh](https://github.com/big-data-lab-umbc/Hybrid-Streaming-Analytics-on-Edge-Cloud/blob/main/install_depandencies.sh) and [stream_training.py](https://github.com/big-data-lab-umbc/Hybrid-Streaming-Analytics-on-Edge-Cloud/blob/main/stream_training.py) file to the instance. Next, prepare the EC2 software environment via ``bash install_depandencies.sh``.

2. Create the two Lambda functions via [link](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions). The function code source is in [folder](https://github.com/big-data-lab-umbc/Hybrid-Streaming-Analytics-on-Edge-Cloud/tree/main/lambda).

### Steps

1. Set up Greengrass in RPi edges by following Step 1-3 in [link](https://docs.aws.amazon.com/greengrass/v2/developerguide/getting-started.html).

2. Now, make sure the Greengrass core devices Status is exact **Healthy**. Then let's continue deploy our customized application. 

3. Put all greengrass component folders to RPi. For example the [greengrass_packages_edgetocloud_hybridlearning](./greengrass_packages_edgetocloud_hybridlearning). The path I used here is ``/home/pi/Downloads/greengrass_packages_edgetocloud_hybridlearning``.

4. Deploy all components in AWS IoT:

```bash
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_streamlearning/recipes --artifactDir ~/Downloads/greengrass_packages_streamlearning/artifacts --merge "StreamLearning-Starly=1.0.0"
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_batchlearning/recipes --artifactDir ~/Downloads/greengrass_packages_batchlearning/artifacts --merge "BatchLearning-Starly=1.0.0"
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_edgetocloud_hybridlearning/recipes --artifactDir ~/Downloads/greengrass_packages_edgetocloud_hybridlearning/artifacts --merge "EdgeToCloud-HybirdLearning-Starly=1.0.0"
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_publishdata/recipes --artifactDir ~/Downloads/greengrass_packages_publishdata/artifacts --merge "MetadataPublishing-Starly=1.0.0"
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_updatemodel/recipes --artifactDir ~/Downloads/greengrass_packages_updatemodel/artifacts --merge "ModelUpdating-Starly=1.0.0"
```

5. Create a topic_list.txt file and put all kafka topics we used in the file. The kafka topics we used includes "batch_input_topic", "batch_topic" and "speed_topic". Then run Kafka Pub/Sub service and publish the metadata:
```bash
cd /home/pi/Downloads/kafka_2.13-3.1.0
bin/zookeeper-server-start.sh config/zookeeper.properties
bin/kafka-server-start.sh config/server.properties
awk -F':' '{ system("/home/pi/Downloads/kafka_2.13-3.1.0/bin/kafka-topics.sh --delete --bootstrap-server localhost:9092 --topic=" $1) }' /home/pi/Downloads/topic_list.txt
awk -F':' '{ system("/home/pi/Downloads/kafka_2.13-3.1.0/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 --topic=" $1 " --partitions=1 --replication-factor=1") }' /home/pi/Downloads/topic_list.txt
python3 /home/pi/Downloads/greengrass_packages_publishdata/artifacts/MetadataPublishing-Starly/1.0.0/metadata_publishing/kafkapublish.py localhost:9092 batch_input_topic /home/pi/Downloads/greengrass_packages_publishdata/artifacts/MetadataPublishing-Starly/1.0.0/metadata_publishing/sample_data/test.csv 29999
```

6. Run the following command to verify that application component runs and prints the result.
```bash
sudo tail -f /greengrass/v2/logs/EdgeToCloud-HybirdLearning-Starly.log
```

You can also see the result print out via [MQTT test client](https://us-west-2.console.aws.amazon.com/iot/home?region=us-west-2#/test) in AWS IoT console.

7. Check the results in AWS S3 bucket. The bucket we used includes "edge-to-cloud-hybrid-learning", "edge-to-cloud-metadata" and "edge-to-cloud-streaming-model".

> Note: If you are using different edge like Jetson Nano, you need to change the [recipe.json](./greengrass_packages_publishdata/recipes/recipe.json#L38) file. For  example, change platform[architecture]:"arm" to "aarch64".

### Citation
If you use this code for your research, please cite our [paper](https://arxiv.org/abs/2205.04622):
```bash
@misc{https://doi.org/10.48550/arxiv.2205.04622,
  doi = {10.48550/ARXIV.2205.04622},
  url = {https://arxiv.org/abs/2205.04622},
  author = {Wang, Xin and Khan, Azim and Wang, Jianwu and Gangopadhyay, Aryya and Busart, Carl E. and Freeman, Jade},
  keywords = {Distributed, Parallel, and Cluster Computing (cs.DC), Machine Learning (cs.LG), Networking and Internet Architecture (cs.NI), FOS: Computer and information sciences, FOS: Computer and information sciences},
  title = {An Edge-Cloud Integrated Framework for Flexible and Dynamic Stream Analytics},
  publisher = {arXiv},
  year = {2022},
  copyright = {Creative Commons Attribution 4.0 International}
}
```

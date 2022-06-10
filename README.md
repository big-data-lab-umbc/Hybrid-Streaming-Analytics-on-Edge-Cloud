# Hybrid-Streaming-Analytics-on-Edge-Cloud

## Deploy customized application (Hybrid Analytics) in AWS IoT

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


### Steps

1. For speed layer model training, we need more powerful machine like the EC2 instance. We need to initial a c5.4xlarge EC2 instance in our example. Then copy [install_depandencies.sh](https://github.com/big-data-lab-umbc/Hybrid-Streaming-Analytics-on-Edge-Cloud/blob/main/install_depandencies.sh) and [stream_training.py](https://github.com/big-data-lab-umbc/Hybrid-Streaming-Analytics-on-Edge-Cloud/blob/main/stream_training.py) file to the instance. Next, prepare the EC2 software environment via ``bash install_depandencies.sh``.

2. Set up Greengrass in RPi edges by following Step 1-3 in [link](https://docs.aws.amazon.com/greengrass/v2/developerguide/getting-started.html).

3. Now, make sure the Greengrass core devices Status is exact **Healthy**. Then let's continue deploy our customized application. 

4. Put all greengrass component folders to RPi. For example the [greengrass_packages_edgetocloud_hybridlearning](./greengrass_packages_edgetocloud_hybridlearning). The path I used here is ``/home/pi/Downloads/greengrass_packages_edgetocloud_hybridlearning``.

5. Deploy all components in AWS IoT:

```bash
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_streamlearning/recipes --artifactDir ~/Downloads/greengrass_packages_streamlearning/artifacts --merge "StreamLearning-Starly=1.0.0"
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_batchlearning/recipes --artifactDir ~/Downloads/greengrass_packages_batchlearning/artifacts --merge "BatchLearning-Starly=1.0.0"
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_edgetocloud_hybridlearning/recipes --artifactDir ~/Downloads/greengrass_packages_edgetocloud_hybridlearning/artifacts --merge "EdgeToCloud-HybirdLearning-Starly=1.0.0"
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_publishdata/recipes --artifactDir ~/Downloads/greengrass_packages_publishdata/artifacts --merge "MetadataPublishing-Starly=1.0.0"
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_updatemodel/recipes --artifactDir ~/Downloads/greengrass_packages_updatemodel/artifacts --merge "ModelUpdating-Starly=1.0.0"
```

6. Create a topic_list.txt file and put all kafka topics we used in the file. The kafka topics we used includes "batch_input_topic", "batch_topic" and "speed_topic". Then run Kafka Pub/Sub service and publish the metadata:
```bash
cd /home/pi/Downloads/kafka_2.13-3.1.0
bin/zookeeper-server-start.sh config/zookeeper.properties
bin/kafka-server-start.sh config/server.properties
awk -F':' '{ system("/home/pi/Downloads/kafka_2.13-3.1.0/bin/kafka-topics.sh --delete --bootstrap-server localhost:9092 --topic=" $1) }' /home/pi/Downloads/topic_list.txt
awk -F':' '{ system("/home/pi/Downloads/kafka_2.13-3.1.0/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 --topic=" $1 " --partitions=1 --replication-factor=1") }' /home/pi/Downloads/topic_list.txt
python3 /home/pi/Downloads/greengrass_packages_publishdata/artifacts/MetadataPublishing-Starly/1.0.0/metadata_publishing/kafkapublish.py localhost:9092 batch_input_topic /home/pi/Downloads/greengrass_packages_publishdata/artifacts/MetadataPublishing-Starly/1.0.0/metadata_publishing/sample_data/test.csv 29999
```

7. Run the following command to verify that application component runs and prints the result.
```bash
sudo tail -f /greengrass/v2/logs/EdgeToCloud-HybirdLearning-Starly.log
```

You can also see the result print out via [MQTT test client](https://us-west-2.console.aws.amazon.com/iot/home?region=us-west-2#/test) in AWS IoT console.

8. Check the results in AWS S3 bucket. The bucket we used includes "edge-to-cloud-hybrid-learning", "edge-to-cloud-metadata" and "edge-to-cloud-streaming-model".

> Note: If you are using different edge like Jetson Nano, you need to change the [recipe.json](./greengrass_packages_publishdata/recipes/recipe.json#L38) file. For  example, change platform[architecture]:"arm" to "aarch64".

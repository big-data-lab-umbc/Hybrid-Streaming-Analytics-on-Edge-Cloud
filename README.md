# Hybrid-Streaming-Analytics-on-Edge-Cloud

## Deploy customized application (Hybrid Analytics) in AWS IoT

### Prerequirement in RPi

We use Debian11 (Bullseye) in RPi4 with Python3.8.

For image classification:
```bash
sudo apt-get install libopenjp2-7 libilmbase23 libopenexr-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libgtk-3-0 libwebp-dev
sudo pip3 install opencv-python
sudo python3 -m pip install tflite-runtime==2.5.0
sudo python3 -m pip install awsiotsdk
sudo python3 -m pip install awscrt

sudo python3 -m pip install pandas
sudo pip3 install scikit-learn scipy

wget https://dlcdn.apache.org/spark/spark-3.0.3/spark-3.0.3-bin-hadoop2.7.tgz
tar xvf spark-*
sudo mv spark-3.0.3-bin-hadoop2.7 spark
echo "PATH=/home/pi/spark/bin:/home/pi/spark/sbin:$PATH" >> ~/.profile
echo "PYSPARK_PYTHON=/usr/bin/python3" >> ~/.profile
echo "PYSPARK_DRIVER_PYTHON=/usr/bin/python3" >> ~/.profile
echo "SPARK_HOME=/home/pi/spark" >> ~/.profile
source ~/.profile
```


### Steps

1. Set up Greengrass in RPi edges by following Step 1-3 in [link](https://docs.aws.amazon.com/greengrass/v2/developerguide/getting-started.html).

2. Now, make sure the Greengrass core devices Status is exact **Healthy**. Then let's continue deploy our customized application. 

3. Put the [greengrass_packages_hybridlearning](./greengrass_packages_hybridlearning) folder to RPi. The path I used here is ``/home/pi/Downloads/greengrass_packages_hybridlearning``.

4. Deploy this application in AWS IoT:

```bash
sudo /greengrass/v2/bin/greengrass-cli deployment create --recipeDir ~/Downloads/greengrass_packages_hybridlearning/recipes --artifactDir ~/Downloads/greengrass_packages_hybridlearning/artifacts --merge "HybirdLearning-Starly=1.0.0"
sudo /greengrass/v2/bin/greengrass-cli component restart  --names "HybirdLearning-Starly"
```

5. Run the following command to verify that application component runs and prints the result.
```bash
sudo tail -f /greengrass/v2/logs/HybirdLearning-Starly.log
```

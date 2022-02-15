# Hybrid-Streaming-Analytics-on-Edge-Cloud

## Deploy customized application (image classification) in AWS IoT

### Prerequirement in RPi

We use Debian11 (Bullseye) in RPi4 with Python3.8.

```bash
sudo apt-get install libopenjp2-7 libilmbase23 libopenexr-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libgtk-3-0 libwebp-dev
pip3 install opencv-python
python3 -m pip install tflite-runtime==2.5.0
python3 -m pip install awsiotsdk
python3 -m pip install awscrt
```

To enable usb webcam (not embedded cameras) in RPi4, also install depandencies use ``sudo apt install fswebcam && sudo apt install ffmpeg``. Check if the webcam works in [link](https://raspberrypi-guide.github.io/electronics/using-usb-webcams).

### Steps

1. Set up Greengrass in RPi edges by following Step 1-3 in [link](https://docs.aws.amazon.com/greengrass/v2/developerguide/getting-started.html).

2. Now, make sure the Greengrass core devices Status is exact **Healthy**. Then let's continue deploy our customized application. 

3. Put the [greengrass_packages_imageclassification](./greengrass_packages_imageclassification) folder to RPi. The path I used here is ``/home/pi/Downloads/greengrass_packages_imageclassification``.

4. Deploy this application in AWS IoT:

```bash
sudo /greengrass/v2/bin/greengrass-cli deployment create \
--recipeDir /home/pi/Downloads/greengrass_packages_imageclassification/recipes \
--artifactDir /home/pi/Downloads/greengrass_packages_imageclassification/artifacts \
--merge "ImageClassification-Starly=1.0.0"
```

5. Run the following command to verify that application component runs and prints the result.
```bash
sudo tail -f /greengrass/v2/logs/ImageClassification-Starly.log
```

6. (Optional) Let's try to change configuration by using config update json file.

    - While change to use another image for classification, you can update deployment by ``sudo /greengrass/v2/bin/greengrass-cli deployment create --merge "ImageClassification-Starly=1.0.0" --update-config /home/pi/Downloads/greengrass_packages_imageclassification/ImageClassification-Starly-config-update-image.json``

    - While change to use usb webcam to capture images for classification, you can update deployment by ``sudo /greengrass/v2/bin/greengrass-cli deployment create --merge "ImageClassification-Starly=1.0.0" --update-config /home/pi/Downloads/greengrass_packages_imageclassification/ImageClassification-Starly-config-update.json``

7. (Optional) Then restart the deployment by ``sudo /greengrass/v2/bin/greengrass-cli component restart  --names "ImageClassification-Starly"``. After that, use step 5 to check the logs.

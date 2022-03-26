#!/bin/sh

set -e

sudo apt install -y unzip git 

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install

curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo service docker start && sudo usermod -a -G docker ubuntu && sudo chmod 666 /var/run/docker.sock
docker pull starlyxxx/hybrid-learning-edge-to-cloud && mkdir /home/ubuntu/stream_layer_model && mkdir /home/ubuntu/metadata

git clone https://github.com/big-data-lab-umbc/Hybrid-Streaming-Analytics-on-Edge-Cloud.git
cp /home/ubuntu/Hybrid-Streaming-Analytics-on-Edge-Cloud/stream_training.py /home/ubuntu/

mkdir /home/ubuntu/metadata
mkdir /home/ubuntu/stream_layer_model
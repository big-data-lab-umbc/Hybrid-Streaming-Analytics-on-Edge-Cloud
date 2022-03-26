FROM ubuntu:18.04

RUN apt-get update && \
  apt-get install -y software-properties-common && \
  add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update

RUN apt-get install -y build-essential python3-pip python3-setuptools python3.6-dev
RUN apt-get install -y git wget zip unzip vim curl

RUN python3 -m pip install --upgrade pip setuptools
RUN python3 -m pip install tensorflow==2.2.0 cmake keras pandas scikit-learn scipy boto3 pyspark==3.0.3

RUN apt install -y default-jdk
RUN ln -s /usr/bin/python3 /usr/bin/python

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install

RUN wget https://dlcdn.apache.org/spark/spark-3.0.3/spark-3.0.3-bin-hadoop2.7.tgz
RUN tar xvf spark-*
RUN mv spark-3.0.3-bin-hadoop2.7 spark
RUN echo "PYSPARK_PYTHON=/usr/bin/python3" >> ~/.profile
RUN echo "PYSPARK_DRIVER_PYTHON=/usr/bin/python3" >> ~/.profile

RUN rm -rf awscliv2.zip
RUN rm -rf spark-3.0.3-bin-hadoop2.7.tgz

WORKDIR /root/

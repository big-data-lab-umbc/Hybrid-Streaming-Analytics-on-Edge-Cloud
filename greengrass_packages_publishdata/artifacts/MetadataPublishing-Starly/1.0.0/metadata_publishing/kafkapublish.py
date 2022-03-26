#python3 kafkapublish.py localhost:9092 batch_input_topic sample_data/temperature_train.csv 2500
from time import sleep
from json import dumps
from kafka import KafkaProducer
import numpy as np
import math
import time
import datetime as dt
import sys

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print("Usage: streamsourcedata.py <hostname:port> <topic>", file=sys.stderr)
        sys.exit(-1)

    broker = sys.argv[1]
    topic = sys.argv[2]
    src_file = str(sys.argv[3])
    max_line = int(sys.argv[4])

    f = open(src_file,"+r")
    lines = f.readlines()

    start = time.time()
    l = 0
    for line in lines:
        if l == 0:
            l+=1
            continue
        else:
            msg = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")  + ',' + line  #add streaming timestamp for data
            msg = line.replace("\n","")
            l+=1
        if msg[-2] == ",":
            continue

        # print()
        producer = KafkaProducer(bootstrap_servers=[broker],
                             value_serializer=lambda x:
                             dumps(x).encode('utf-8'),
                             api_version=(3,1))
        producer.send(topic, value=msg)
        #sleep(1)

        if l == max_line+1:
            break

    end = time.time()
    print("Success genenrate %s streaming records, latency = %s s, throughput = %s records/s."%(str(max_line),str(end-start),str(max_line/(end-start))))

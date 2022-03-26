from time import sleep
from json import dumps
import numpy as np
import math
import datetime as dt
import random as rn
import sys

if __name__ == '__main__':
    f = open('test.csv', "+r")
    out_str = []
    lines = f.readlines()
    j = 0
    len_for_data = 30000

    for line in lines:
        if j==0:
            out_str.append(line)
            j+=1
            continue
        x0, x1, x2, x3, x4, x5 = line.split(",") 

        # x1 = round(0.0012 * j + float(x1),2)  #for gradual drift
        # x2 = round(0.002 * j + float(x2),2)
        # x3 = round(0.0008 * j + float(x3),2)
        # x4 = round(0.0016 * j + float(x4),2)
        # x5 = round(0.001 * j + float(x5),2)

        drift = rn.randint(1,len_for_data)      #for abrupt drift
        x1 = round(0.0012 * drift + float(x1),2)  
        x2 = round(0.002 * drift + float(x2),2)
        x3 = round(0.0008 * drift + float(x3),2)
        x4 = round(0.0016 * drift + float(x4),2)
        x5 = round(0.001 * drift + float(x5),2)

        out_str.append(str(x0) +','+ str(x1) +','+ str(x2)+','+ str(x3)+','+ str(x4)+','+ str(x5))

        j+=1

    onp = np.array(out_str)
    # np.savetxt('./train_gradual_drift.csv', onp, delimiter=",", fmt="%s")
    np.savetxt('./test_abrupt_drift.csv', onp, delimiter=",", fmt="%s")
import pandas as pd
import math
import matplotlib.pyplot as plt
import glob


mylist = [f for f in glob.glob("./output/(0.3s+0.7b,60s)edge-to-cloud-hybrid-learning/*.csv")]
dataframes_list = []
for i in mylist:
    df1 = pd.read_csv(i, sep=',', header=0)
    dataframes_list.append(df1)
df = dataframes_list[0]
for i in range(1,len(mylist)):
    df = df.append(dataframes_list[i], ignore_index=True)
df = df.dropna().sort_values(by=['TS']).drop_duplicates(subset=['TS'], keep='first')

# df = pd.read_csv('./scalability/10000_dynamic_cores.csv', sep=',', header=0)
# df = df.dropna().sort_values(by=['TS'])
# print(len(df),df.head())

#df = df.drop_duplicates(subset=['Speed_RMSE', 'Batch_RMSE', 'Wt_RMSE'], keep='first')
df = df.drop_duplicates(subset=['TS'], keep='first')
print(len(df))

df["End_time"] = df[['Speed_Latency_End','Batch_Latency_End']].max(axis=1)
df["Start_time"] = df[['Speed_Latency_Start','Batch_Latency_Start']].min(axis=1)
df["Total_Latency"] = df["End_time"]-df["Start_time"]+df["Wt_Latency"]
df_temp = df[["Total_Latency", "TS"]]
df_temp = df_temp.drop_duplicates(subset=["Total_Latency"], keep='first')
print(len(df_temp),df_temp.head(),list(df_temp.columns))

# average_sp_latency = round(df["Speed_Latency"].mean(),3)
# average_bt_latency = round(df["Batch_Latency"].mean(),3)
# average_wt_latency = round(df["Wt_Latency"].mean(),3)
# average_total_latency = round(df["Total_Latency"].mean(),3)

df_window = df[['Speed_RMSE', 'Batch_RMSE', 'Wt_RMSE','Speed_Latency','Batch_Latency','Wt_Latency',"Total_Latency"]]
df_window = df_window.groupby(df_window.columns.tolist()).size().reset_index().rename(columns={0:'counts'})
print(len(df_window),df_window.head(),list(df_window.columns))

df_window2 = df_window.join(df_temp.set_index('Total_Latency'), on='Total_Latency')
df_window2 = df_window2.sort_values(by=['TS'])
print(len(df_window2),df_window2.head(),list(df_window2.columns))

df_window2["Speed_TPS"] = df_window2["counts"]/df_window2["Speed_Latency"]
df_window2["Batch_TPS"] = df_window2["counts"]/df_window2["Batch_Latency"]
df_window2["Wt_TPS"] = df_window2["counts"]/df_window2["Wt_Latency"]
df_window2["Total_TPS"] = df_window2["counts"]/df_window2["Total_Latency"]

sp_tps = df_window2['Speed_TPS'].tolist()
bt_tps = df_window2['Batch_TPS'].tolist()
wt_tps = df_window2['Wt_TPS'].tolist()
total_tps = df_window2['Total_TPS'].tolist()
counts = df_window2["counts"].tolist()
print(counts)

# ave_sp_tps = sum(sp_tps) / len(sp_tps)
# ave_bt_tps = sum(bt_tps) / len(bt_tps)
# ave_wt_tps = sum(wt_tps) / len(wt_tps)
# ave_total_tps = sum(total_tps) / len(total_tps)

# print(str(ave_sp_tps)+"\n"+str(ave_bt_tps)+"\n"+str(ave_wt_tps)+"\n"+str(ave_total_tps))

sp_latency = df_window2['Speed_Latency'].tolist()
bt_latency = df_window2['Batch_Latency'].tolist()
wt_latency = df_window2['Wt_Latency'].tolist()
total_latency = df_window2['Total_Latency'].tolist()

# ave_sp_latency = sum(sp_latency) / len(sp_latency)
# ave_bt_latency = sum(bt_latency) / len(bt_latency)
# ave_wt_latency = sum(wt_latency) / len(wt_latency)
# ave_total_latency = sum(total_latency) / len(total_latency)

# print(str(ave_sp_latency)+"\n"+str(ave_bt_latency)+"\n"+str(ave_wt_latency)+"\n"+str(ave_total_latency))

sp_rmse = df_window2['Speed_RMSE'].tolist()
bt_rmse = df_window2['Batch_RMSE'].tolist()
wt_rmse = df_window2['Wt_RMSE'].tolist()

# ave_sp_rmse = sum(sp_rmse) / len(sp_rmse)
# ave_bt_rmse = sum(bt_rmse) / len(bt_rmse)
# ave_wt_rmse = sum(wt_rmse) / len(wt_rmse)

# print(str(ave_sp_rmse)+"\n"+str(ave_bt_rmse)+"\n"+str(ave_wt_rmse))

plt.plot(sp_rmse, label='Speed_RMSE') 
plt.plot(bt_rmse, label='Batch_RMSE') 
plt.plot(wt_rmse, label='Wt_RMSE')
#plt.plot(total_latency, label='Total_Latency')

#plt.title('RMSE for VAR Model, dynamic cores\n(sp_l=%ss, bt_l=%ss, wt_l=%ss, t_l=%ss)'%(str(average_sp_latency),str(average_bt_latency),str(average_wt_latency),str(average_total_latency)))
plt.title('RMSE for LSTM Model, 10000 records with dynamic cores.')
plt.xlabel('Streaming time window')
plt.ylabel('Rmse')
plt.legend()
plt.savefig("./lstm_rmse_with_10000_dynamic_cores.png")

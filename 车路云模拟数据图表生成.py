import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pyproj import Transformer
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

#1.模拟生成车路协同交通流数据
def generate_vehicle_data(num_vehicles=50,time_steps=120):
    vehicles_ids=[f'V{str(i).zfill(3)}' for i in range(1,num_vehicles+1)]
    timestamps=pd.date_range(start='2025-08-01 08:00:00',periods=time_steps,freq='5s')
    data=[]
    for vid in vehicles_ids:
        base_lon=116.3+np.random.random()*0.1
        base_lat=39.9+np.random.random()*0.1
        lon_noise=np.random.normal(0,0.0001,time_steps)
        lat_noise=np.random.normal(0,0.0001,time_steps)
        speed=np.clip(20+np.random.random(time_steps)*30+np.sin(np.linspace(0,2*np.pi,time_steps))*10,0,60)
        for i, ts in enumerate(timestamps):
            data.append({'vehicle_id':vid,'timestamp':ts,'wgs84_lon':base_lon+lon_noise[i],'wgs84_lat':base_lat+lat_noise[i],'speed_kmh':speed[i],'lane_id':np.random.choice(['L1','L2','L3'])})
    df=pd.DataFrame(data)
    abnormal_idx=np.random.choice(df.index,size=int(len(df)*0.01),replace=False)
    df.loc[abnormal_idx,'speed_kmh']=np.random.random(len(abnormal_idx))*80+120
    missing_idx=np.random.choice(df.index,size=int(len(df)*0.005),replace=False)
    df.loc[missing_idx,['wgs84_lon','wgs84_lat']]=np.nan
    return df
        
#2.数据清洗
def clean_vehicle_data(df):
    """处理缺失值，重复值，异常值"""
    print(f'原始数据集：{len(df)}条')
    df_clean=df.drop_duplicates(subset=['vehicle_id','timestamp'])
    df_clean['wgs84_lon']=df_clean.groupby('vehicle_id')['wgs84_lon'].fillna(method='ffill')
    df_clean['wgs84_lat']=df_clean.groupby('vehicle_id')['wgs84_lat'].fillna(method='ffill')
    df_clean['speed_kmh']=df_clean.groupby(['lane_id','timestamp'])['speed_kmh'].transform(lambda x:x.fillna(x.mean()).fillna(df_clean['speed_kmh'].mean()))
    df_clean=df_clean.dropna(subset=['speed_kmh','wgs84_lon','wgs84_lat'])
    speed_median=df_clean.groupby('vehicle_id')['speed_kmh'].transform('median')
    df_clean.loc[(df_clean['speed_kmh']>120) | (df_clean['speed_kmh']<0),'speed_kmh']=speed_median
    df_clean['hour']=df_clean['timestamp'].dt.hour
    df_clean['minute']=df_clean['timestamp'].dt.minute
    df_clean['second']=df_clean['timestamp'].dt.second
    print(f'清洗后数据：{len(df_clean)}条')
    return df_clean

#3.地理坐标的转换
def wgs84_to_gcj02 (df):
    df_copy=df.copy()
    '''将WGS84(GPS原始坐标)转换为GCJ02(中国国测局加密坐标)'''
    transformer=Transformer.from_crs('EPSG:4326','EPSG:4490',always_xy=True)
    gcj02_lon,gcj02_lat=transformer.transform(xx=df_copy['wgs84_lon'].values,yy=df_copy['wgs84_lat'].values)
    df_copy['gcj02_lon']=gcj02_lon
    df_copy['gcj02_lat']=gcj02_lat
    return df_copy

#4.计算车间时距 哈佛辛公式 sin²(Δφ/2) + cosφ₁×cosφ₂×sin²(Δλ/2)，其中 φ 为纬度，λ 为经度
def calculate_time_headway(df):
    '''计算车间时距，相邻车辆的时间差'''
    def haversine_distance(lon1,lat1,lon2,lat2):
        '''计算两点间的地球表面距离'''
        lon1,lat1,lon2,lat2=map(np.radians,[lon1,lat1,lon2,lat2])
        dlon=lon2-lon1
        dlat=lat2-lat1
        a=np.sin(dlat/2)**2+np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
        c=2*np.arcsin(np.sqrt(a))
        return  c*6371000
    df_distance=[]
    for vid,group in df.groupby('vehicle_id'):
        group_sorted=group.sort_values('timestamp').reset_index(drop=True)
        distances= haversine_distance(group_sorted['gcj02_lon'].shift(1),group_sorted['gcj02_lat'].shift(1),group_sorted['gcj02_lon'],group_sorted['gcj02_lat'])
        group_sorted['cumulative_distance_m']=distances.fillna(0).cumsum()
        df_distance.append(group_sorted)
    df=pd.concat(df_distance,ignore_index=True)
    time_headway_data=[]
    for (lane,ts),group in df.groupby(['lane_id','timestamp']):
        group_sorted=group.sort_values('cumulative_distance_m',ascending=True).reset_index(drop=True)
        if  len(group_sorted)<2:
             continue
        for i in range(len(group_sorted)-1):
            rear_car=group_sorted.iloc[i]
            front_car=group_sorted.iloc[i+1]
            distance_between=front_car['cumulative_distance_m']-rear_car['cumulative_distance_m']
            rear_speed_ms=rear_car['speed_kmh']*1000/3600
            time_headway=distance_between/rear_speed_ms if rear_speed_ms>0 else np.nan
            time_headway_data.append({'lane_id':lane,'timestamp':ts,'front_car_vehicle':front_car['vehicle_id'],'rear_vehicle_id':rear_car['vehicle_id'],'distance_between_m':distance_between,'rear_speed_kmh':rear_car['speed_kmh'],'time_headway_s':time_headway})
    df_headway=pd.DataFrame(time_headway_data)
    df_headway=df_headway[(df_headway['time_headway_s']>0) & (df_headway['time_headway_s']<30)]
    return df,df_headway
    
    #5.可视化分析
def plot_vehicle_analysis(df,df_headway):
    plt.rcParams['font.sans-serif']=['SimHei']
    fig,axes=plt.subplots(2,2,figsize=(16,12))
    fig.suptitle('车路协同交通流数据处理结果',fontsize=16,fontweight='bold')
    lane_speed=df.groupby(['timestamp','lane_id'])['speed_kmh'].mean().unstack()
    for lane in lane_speed.columns:
        axes[0,0].plot(lane_speed.index,lane_speed[lane],label=f'车道{lane}')
    axes[0,0].set_title('各车道平均速度时序变化',fontweight='bold')
    axes[0,0].set_xlabel('时间')
    axes[0,0].set_ylabel('平均速度(km/h)')
    axes[0,0].legend()
    axes[0,0].grid(alpha=0.3)

    for lane,color in zip(['L1','L2','L3'],['red','blue','green']):
        lane_data=df[df['lane_id']==lane]
    axes[0,1].scatter(lane_data['gcj02_lon'],lane_data['gcj02_lat'],c=color,label=f'车道{lane}',s=10,alpha=0.6)
    axes[0,1].set_title('车辆行驶轨迹分布(GCJ02坐标)',fontweight='bold')
    axes[0,1].set_xlabel('GCJ02经度')
    axes[0,1].set_ylabel('GCJ02纬度')
    axes[0,1].legend()
    axes[0,1].grid(alpha=0.3)

    for lane,color in zip(['L1','L2','L3'],['red','blue','green']):
        lane_headway=df_headway[df_headway['lane_id']==lane]['time_headway_s']
    axes[1,0].hist(lane_headway,bins=20,alpha=0.5,label=f'车道{lane}',color=color)
    axes[1,0].set_title('车间时距分布(安全阈值:>2秒)',fontweight='bold')
    axes[1,0].set_xlabel('车间时距(秒)')
    axes[1,0].set_ylabel('频次')
    axes[1,0].axvline(x=2,color='black',linestyle='--',label='安全阈值')
    axes[1,0].legend()
    axes[1,0].grid(alpha=0.3)

    for lane,color in zip(['L1','L2','L3'],['red','blue','green']):
        lane_data=df_headway[df_headway['lane_id']==lane]
    axes[1,1].scatter(lane_data['rear_speed_kmh'],lane_data['distance_between_m'],c=color,label=f'车道{lane}',s=10,alpha=0.6)
    axes[1,1].set_title('后车速度与车间距离相关性',fontweight='bold')
    axes[1,1].set_xlabel('后车速度(kmh)')
    axes[1,1].set_ylabel('车间距离(米)')
    axes[1,1].legend()
    axes[1,1].grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('vehicle_road_cloud_analysis.png',dpi=300,bbox_inches='tight')
    plt.close()
    print('可视化图表已保存为:vehicle_road_cloud_analysis.png')

#6.主函数
if __name__ =='__main__':
    df_raw=generate_vehicle_data(num_vehicles=50,time_steps=120)
    df_clean=clean_vehicle_data(df_raw)
    df_with_gcj02=wgs84_to_gcj02(df_clean)
    df_final,df_headway=calculate_time_headway(df_with_gcj02)
    print('\n=== 关键统计结果 ===')
    print(f'1.平均车速：{df_final["speed_kmh"].mean():.2f}km/h')
    print(f'2.各车道车辆数:\n{df_final.groupby("lane_id")["vehicle_id"].nunique()}')
    print(f'3.平均车间时距：{df_headway["time_headway_s"].mean():.2f}秒')
    print(f'4.时距<2秒(危险场景)占比：{(df_headway["time_headway_s"]<2).sum() / len(df_headway)*100:.2f}%')
    plot_vehicle_analysis(df_final,df_headway)


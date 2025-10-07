import pandas as pd
import numpy as np
from datetime import datetime ,timedelta
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import os

plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False 

class TimeAnalyzer:
    def __init__(self):
        '''初始化时间间隔'''
        self.days = ['周一','周二','周三','周四','周五','周六','周日']
        self.activities = {day:[] for day in self.days}
        self.categories = set()
        self.data_file = 'TimeAnalyzer.csv'
        self.load_data()
    def add_activity(self, day , activity_name , category ,hours , minutes=0):
        '''添加活动记录'''
        total_hours = hours + minutes/ 60
        self.activities[day].append({'name':activity_name,'category':category,'hours':total_hours})
        self.categories.add(category)
        print(f'已添加:{day} {activity_name} ({category}) - {hours}小时{minutes}分钟')
    def display_daily_summary(self, day):
        '''显示某天的时间摘要'''
        print(f'\n{day}时间利用摘要:')
        activities = self.activities[day]
        if not activities:
            print(' 没有记录的活动')
            return
        
        total_time = 0 
        for i, activity in enumerate(activities, 1):
            hours = activity['hours']
            hours_int = int(hours)
            minutes =int((hours - hours_int)*60)
            print(f' {i}.{activity['name']} ({activity['category']}): {hours_int}小时{minutes}分钟')
            total_time += hours
        hours_int = int(total_time)
        minutes = int((total_time - hours_int)*60)
        print(f'\n总计记录时间:{hours_int}小时{minutes}分钟')
        print(f'  未记录时间：{24 - hours-int}小时{60 }')
    
    def display_weekly_summary(self):
        '''显示一周的时间利用摘要'''
        print('\n一周时间利用摘要')

        category_total = {category: 0 for category in self.categories}
        daily_total = {day: 0 for day in self.days}

        for day in self.days:
            for activity in self.activities[day]:
                category_total[activity['category']] += activity['hours']
                daily_total[day] += activity['hours']

        print('\n每日记录时间:')
        for day in self.days:
            hours_int = int(daily_total[day])
            minutes = int((daily_total[day] - hours_int) * 60)
            print(f'{day}:{hours_int}小时{minutes}分钟')
        print('\n各类别总时间:')
        for category, total in category_total.items():
            hours_int = int(total)
            minutes = int((total - hours_int)*60)
            print(f'{category}:{hours_int}小时{minutes}分钟')
        
        total_weekly = sum(daily_total.values())
        avg_daily = total_weekly / 7
        hours_int = int(total_weekly)
        minutes = int((total_weekly - hours_int)*60)
        avg_hours = int(avg_daily)
        avg_minutes = int((avg_daily - avg_hours)*60)

        print(f'\n一周总记录时间:{hours_int}小时{minutes}分钟')
        print(f'平均每日记录时间:{avg_hours}小时{avg_minutes}分钟')

    def visualize_daily(self,day):
        '''可视化某天的时间利用情况'''
        activities = self.activities[day]
        if not activities:
            print(f'\n{day}没有可视化的数据')
            return
        labels = [f'{a['name']}({a['category']})' for a in activities]
        sizes = [a['hours'] for a in activities]

        plt.figure(figsize=(10,7))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%',startangle=90)
        plt.axis('equal')
        plt.title(f'{day}时间利用分布')
        plt.tight_layout()
        plt.show()

    def visualize_weekly_by_category(self):
        '''按类别可视化一周的时间利用情况'''
        if not self.categories:
            print(f'\n没有可视化的数据')
            return
        category_data = {category: [0 for _ in self.days] for category in self.categories}
        for day_idx , day in enumerate(self.days):
            for activity in self.activities[day]:
                category_data[activity['category']]
                category_data[category][day_idx] += activity['hours'] 
        fig, ax = plt.subplots(figsize=(12,8))
        bottom = np.zeros(len(self.days))

        for category , hours in category_data.items():
            p  = ax.bar(self.days, hours, bottom=bottom, label=category)
            bottom += np.array(hours)

        ax.set_title('一周时间利用情况(按类别)')
        ax.set_xlabel('星期')
        ax.set_ylabel('小时')
        ax.legend(loc='upper right')
        plt.tight_layout()
        plt.show()

    def visualize_category_proportion(self):
        '''可视化各类型时间占比'''
        if not self.categories:
           print('\n没有可视化的时间数据')
           return
    
        category_total = {category: 0 for category in self.categories}
        for day in self.days:
            for activity in self.activities[day]:
                category_total[activity['category'] ]+= activity['hours']

        category_total ={k: v for k,v in category_total.items() if v>0}

        if not category_total:
            print('\n没有可视化的数据')
            return
        labels = list(category_total.keys())
        sizes = list(category_total.values())
        
        plt.figure(figsize=(10,7))
        plt.pie(sizes, labels=labels, autopct='%1.1f%', startangle=90)
        plt.axis('equal')
        plt.title('一周各类时间占比')
        plt.tight_layout()
        plt.show()

    def save_data(self):
        '''保存数据到CSV文件'''
        data = []
        for day in self.days:
            for activity in self.activities[day]:
                data.append({'day':day,'activity':activity['name'],'category':activity['category'],'hours':activity['hours']})

        df = pd.DataFrame(data)
        df.to_csv(self.data_file, index=False)
        print(f'\n数据已保存到:{self.data_file}')
    def load_data(self):
        '''从CSV文件加载数据''' 
        if os.path.exists(self.data_file):
            try:
                df = pd.read_csv(self.data_file)
                self.activities = {day: []for day in self.days }
                self.categories = set()
        
                for _, row in df.iterrows():
                    day =row['day']
                    if day in self.days:
                        hours = int(row['hours'])
                        minutes = int((row['hours'] - hours) * 60)   
                        self.add_activity(day,row['activity'],row['category'],row['hours'],0)
                    
                    print('TimeAnalyzer.csv')
            except Exception as e:
                    print(f'加载数据时出错:{str(e)}')
        else:
            print('未找到保存的数据,将从头开始')
def main():
    '''主函数,处理用户交互'''
    analyzer = TimeAnalyzer()
    print('\n =====时间分析利用系统=====')

    while True:
        print('\n请选择操作:')
        print('1.添加活动记录')
        print('2.查看某天的时间摘要')
        print('3.查看一周的时间摘要')
        print('4.可视化某天的时间分布')
        print('5.可视化一天的时间分布(按类别)')
        print('6.可视化各类型时间占比')
        print('7.保存数据')
        print('8.退出系统')

        choice = input('请输入操作编号(1-8):')

        if choice =='1':
           print('\n-----添加活动记录-----')
           day = input('请输入日期（如：周一）：')
           if day not in analyzer.days:
              print('无效日期')
              continue
           
           activity_name = input('请输入活动名称：')
           category = input('请输入活动类别如（工作、学习、休息等）：')

           try:
               hours = float(input('请输入小时数：'))
               if hours <= 0:
                print('小时数必须大于0')
                continue
               analyzer.add_activity(day, activity_name, category, hours)
           except ValueError:
                print('无效的时间输入！请输入整数')

        
        elif choice =='2':
            print('\n-----查看某天的时间摘要-----')
            day = input('请输入日期（如：周一）：')
            if day in analyzer.days:
                analyzer.display_daily_summary(day)
            else:
                print('无效的日期')
        elif choice =='3':
            print('\n-----查看一周时间摘要-----')
            analyzer.display_weekly_summary()

        elif choice =='4':
            print('\n-----可视化某天的时间分布-----')
            day = input('请输入日期（如：周一）：')
            if day in analyzer.days:
                analyzer.visualize_daily(day)
            else:
                print('无效的日期')

        elif choice == '5':
            print('\n-----可视化一周的时间分布-----')
            analyzer.visualize_weekly_by_category()

        elif choice =='6':
            print('\n-----可视化各类时间占比-----')
            analyzer.visualize_category_proportiny()

        elif choice =='7':
            analyzer.save_data()

        elif choice =='8':
            save_befor_exit = input('推出前是否保存数据?(y/n):')
            if save_befor_exit.lower() =='y':
                analyzer.save_data()
            print('感谢使用时间分析利用系统，再见！')
            break
        else:
            print("无效的编号，请重新输入")
if __name__ =='__main__':
    main()
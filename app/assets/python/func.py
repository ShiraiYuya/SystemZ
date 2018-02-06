# -*- coding: utf-8 -*-
"""
関数群
・フーバー回帰の繰り返し最小二乗アルゴリズム
・直線回帰による出力
・移動平均の出力
・祝日判定←これを自動で出来るようにしてからでないと納品できない
・休業日判定
・特殊補正(勘)
・相関用データセット生成
・相関に基づいた週sum予測値の出力
・曜日ごとへの振り分け
・NN確認用データセット
"""
import pdb
import datetime as dt
from datetime import date
import numpy as np
from scipy import stats
import config
import mysql.connector

dbcon = mysql.connector.connect(
database=config.db, 
user=config.user, 
password=config.passwd, 
host=config.host,
buffered=True)
dbcur = dbcon.cursor()

#直線モデル
def f(theta,x):
    return theta[0]+theta[1]*x

#基底関数行列
def phy_mat(x):
    return np.array([np.ones(len(x)),x]).T

#フーバー損失に対する重み
def w(r,eta):
    ans=[]
    for i in range(len(r)):
        if abs(r[i])<=eta:
            #ans.append((1-r[i]**2/eta**2)**2)
            ans.append(1)#フーバー損失を採用
        else:
            #ans.append(0)
            ans.append(eta/abs(r[i]))
    return np.array(ans)

#重み行列
def W_mat(x,y,theta,eta):
    return np.diag(w(f(theta,x)-y,eta))

def kaiki(X,y,X_pred):#X,yに関してモデルを生成しX_predに対して出力を行う
    np.random.seed(621)#再現性をとるために固定
    #etaの定義
    eta=300
    #thetaの初期値を決定
    theta=np.random.randn(2)+np.array([3000,0])
    #解の更新
    for i in range(100):#収束条件
        phy=phy_mat(X)
        W=W_mat(X,y,theta,eta)
        theta=np.dot(np.linalg.inv(np.matmul(phy.T,np.matmul(W,phy))),np.dot(phy.T,np.dot(W,y)))
    return f(theta,X_pred)

#フーバー回帰の繰り返し最小二乗アルゴリズムに基づいた直線回帰によるトレンド値の取得
def make_trend(name, b_weeks, max_day, num, a_weeks=0, rate=None):
    pdb.set_trace()
    target_day=date(2015, 4, 6)
    raw_datas=[]
    dates=[]
    i=0
    while target_day<max_day:
        col_name=name+"_ship"
        dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE date>=%s AND date<%s",(target_day, target_day+dt.timedelta(days=7)))
        total_weight=dbcur.fetchone()[0]
        if total_weight is None:
            total_weight=0
        if rate is not None:
            total_weight/=rate[i]
        raw_datas.append(total_weight[0])
        dates.append(target_day)
        target_day+=dt.timedelta(days=7)
        i+=1

    around_weeks=[]
    trends=[]
    if a_weeks!=0:
        j=0
        for i in range(len(raw_datas)):
            while len(around_weeks)<a_weeks:
                around_weeks.append(raw_datas[j])
                j+=1
            if j>b_weeks+a_weeks:
                del around_weeks[0]
            if j<len(raw_datas):
                around_weeks.append(raw_datas[j])
                j+=1
            n=len(around_weeks)
            X=np.array(range(n))
            y=np.array(around_weeks)
            trends.append(kaiki(X,y,np.array(range(n,n+num))))
#            print(dates[i],format(raw_datas[i]).ljust(7),trends[i])
    else:
        j=0
        for i in range(len(raw_datas)):
            if i<b_weeks:
                trends.append(4000)
            else:
                while len(around_weeks)<b_weeks-1:
                    around_weeks.append(raw_datas[j])
                    j+=1
                if j>b_weeks:
                    del around_weeks[0]
                if j<len(raw_datas):
                    around_weeks.append(raw_datas[j])
                    j+=1
                n=len(around_weeks)
                X=np.array(range(n))
                y=np.array(around_weeks)
                trends.append(kaiki(X,y,np.array(range(n,n+num))))
#            print(dates[i],format(raw_datas[i]).ljust(7),trends[i])
    return dates,raw_datas,trends

#移動平均を用いたトレンド値の取得
def make_trend_idou(name, n_weeks, max_day, rate=None):
    pdb.set_trace()
    target_day=date(2015, 4, 6)
    raw_datas=[]
    dates=[]
    i=0
    while target_day<max_day:
        col_name=name+"_ship"
        dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE date>=%s AND date<%s",(target_day, target_day+dt.timedelta(days=7)))
        total_weight=dbcur.fetchone()[0]
        if total_weight is None:
            total_weight=0
        if rate is not None:
            total_weight/=rate[i]
        raw_datas.append(total_weight)
        dates.append(target_day)
        target_day+=dt.timedelta(days=7)
        i+=1
    idou_ave=[]
    for i in range(len(raw_datas)):
        num=0
        l=0
        for j in range(max(0,i-n_weeks),min(len(raw_datas),i+n_weeks+1)):
            num+=raw_datas[j]
            l+=1
        idou_ave.append(num/l)
    return dates,raw_datas,idou_ave

#祝日判定
def holiday_hantei(target_day):#逐次更新出来るようにする…！
    from datetime import date
    holidays=[date(2015, 4, 29),date(2015, 5, 3),date(2015, 5, 4),date(2015, 5, 5),
              date(2015, 7, 20),date(2015, 9, 21),date(2015, 9, 22),date(2015, 9, 23),
              date(2015, 10, 12),date(2015, 11, 3),date(2015, 11, 23),date(2015, 12, 23),
              date(2015, 8, 13),date(2015, 8, 14),date(2015, 8, 15),date(2015, 8, 16),
              date(2016, 1, 11),date(2016, 2, 11),date(2016, 3, 20),date(2016, 3, 21),
              date(2016, 4, 29),date(2016, 5, 3),date(2016, 5, 4),date(2016, 5, 5),
              date(2016, 7, 18),date(2016, 8, 11),date(2016, 9, 19),date(2016, 9, 22),
              date(2016, 10, 10),date(2016, 11, 3),date(2016, 11, 23),date(2016, 12, 23),
              date(2016, 8, 13),date(2016, 8, 14),date(2016, 8, 15),date(2016, 8, 16),
              date(2017, 1, 9),date(2017, 2, 11),date(2017, 3, 20),date(2017, 4, 29),
              date(2017, 5, 3),date(2017, 5, 4),date(2017, 5, 5),date(2017, 7, 17),
              date(2017, 8, 11),date(2017, 9, 18),date(2017, 9, 23),date(2017, 10, 9),
              date(2017, 11, 3),date(2017, 11, 23),date(2017, 12, 23), 
              date(2017, 8, 13),date(2017, 8, 14),date(2017, 8, 15),date(2017, 8, 16),
              date(2018, 1, 8),date(2018, 2, 11),date(2018, 2, 12),date(2018, 3, 21),
              date(2018, 4, 29),date(2018, 4, 30),date(2018, 5, 3),date(2018, 5, 4),
              date(2018, 5, 5),date(2018, 7, 16),date(2018, 8, 11),date(2018, 9, 17),
              date(2018, 9, 23),date(2018, 9, 24),date(2018, 10, 8),date(2018, 11, 3),
              date(2018, 11, 23),date(2018, 12, 23),date(2018, 12, 24),
              date(2018, 8, 13),date(2018, 8, 14),date(2018, 8, 15),date(2018, 8, 16),
              date(2019, 1, 14),date(2019, 2, 11),date(2019, 3, 20),date(2019, 4, 29),
              date(2019, 5, 3),date(2019, 5, 4),date(2019, 5, 5),date(2019, 5, 6),
              date(2019, 7, 15),date(2019, 8, 11),date(2019, 8, 12),date(2019, 9, 16),
              date(2019, 9, 23),date(2019, 10, 14),date(2019, 11, 3),date(2019, 11, 4),
              date(2019, 11, 23),date(2019, 12, 23),
              date(2019, 8, 13),date(2019, 8, 14),date(2019, 8, 15),date(2019, 8, 16)]
    if target_day in holidays:
        return True
    else:
        return False

#休業判定
def stop_hantei(target_day):
    if (target_day.month==12 and target_day.day==31) or (target_day.month==1 and target_day.day<=3):
        return True
    else:
        return False

#特殊補正
def special_rate(target_day):
    rate=0
    if (target_day.month==12 and target_day.day==31):
        rate=-4.0/7.0*0.9
    elif(target_day.month==1 and target_day.day<=3):
        rate=-(4.0-target_day.day)/7.0*0.5
    if (target_day.month==12 and target_day.day>=24 and target_day.day<=27):
        rate=(28.0-target_day.day)/7.0*0.9
    if target_day>=date(target_day.year,1,1) and target_day<=date(target_day.year,2,8):
        rate=-(80.0-(target_day.month-1.0)*62.0-target_day.day*2)/300
    return rate

#相関を見るためのデータセット生成
def make_soukan(max_day, name="f"):
    pdb.set_trace()
    wd=max_day.weekday()
    target_day_f=date(2015, 4, 6)
    target_day_t=target_day_f+dt.timedelta(days=wd)
    dates=[]
    X=[]
    y=[]
    z=[]
    while target_day_t<max_day:
        col_name=name+"_ship"
        dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE date>=%s AND date<%s" 
                      ,(target_day_f,target_day_t))
        wd_weight_1 = dbcur.fetchone()[0]
        if wd_weight_1 is None:
            wd_weight_1 = 0
        col_name=name+"_morn"
        dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE date=%s" 
                      ,(target_day_t,))
        wd_weight_2 = dbcur.fetchone()[0]
        if wd_weight_2 is None:
            wd_weight_2 = 0
        wd_weight = wd_weight_1 + wd_weight_2
        col_name=name+"_ship"
        dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE date>=%s AND date<%s" 
                      ,(target_day_f,target_day_f+dt.timedelta(days=7)))
        total_weight=dbcur.fetchone()[0]
        if total_weight is None:
            total_weight=0
        if total_weight!=0:
            dates.append(target_day_t)
            X.append(wd_weight)
            y.append(total_weight)
            z.append(wd_weight/total_weight)
        target_day_f+=dt.timedelta(days=7)
        target_day_t+=dt.timedelta(days=7)
    z=np.array(z)
    z=(z-np.mean(z))/np.std(z)
    return_X=[]
    return_y=[]
    for i,zs in enumerate(z):
        if abs(zs) < 1:
            return_X.append(X[i])
            return_y.append(y[i])
    return return_X,return_y

#相関に基づいた週sum予測値の取得
def predict_soukan(target_day,name="f",num=None):#numはこちらから与えることも可能(リアルタイムではこちら？)
    pdb.set_trace()
    if num is None:
        wd=target_day.weekday()
        target_day_t=target_day
        target_day_f=target_day_t-dt.timedelta(days=wd)
        col_name=name+"_ship"
        dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE date>=%s AND date<=%s" 
                      ,(target_day_f,target_day_t))
        wd_num = dbcur.fetchone()[0]
        if wd_num is None:
            wd_num = 0
    else:
        wd_num=num
    X,y=make_soukan(target_day, name)
    slope, intercept, r_value, _, _ = stats.linregress(X, y)
    return intercept+slope*wd_num, wd_num

#曜日ごとへの振り分け
def weeksum_day(max_day, num, name="f"):
    pdb.set_trace()
    wd=(max_day+dt.timedelta(days=1)).weekday()#wdを含み以降の日を対象にする
    col_name=name+"_ship"
    target_day = date(2015, 4, 6)
    ratio=[]
    while target_day<max_day-dt.timedelta(days=wd):
        week=[]
        for i in range(6):
            dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE date=%s" 
                          ,(target_day+dt.timedelta(days=i),))
            weight=dbcur.fetchone()[0]
            if weight is None:
                weight=0
            week.append(weight)
        if week.count(0)==0:
            week=np.array(week[wd:])
            week/=sum(week)
            ratio.append(week)
        target_day += dt.timedelta(days=7)
    ratio=np.array(ratio)
    ratio=np.mean(ratio,axis=0)
    for i in range(1,7-wd):
        if stop_hantei(max_day+dt.timedelta(days=i)):
            ratio[i-1]=0
    ratio/=np.sum(ratio)
    return ratio*num

#NN確認用データセット
test_X=[
    [0,0,0,0,1,1,0,0,0,0,1],
    [0,0,0,0,1,1,1,0,0,0,0],
    [0,0,0,1,1,1,0,0,0,0,0],
    [0,0,0,0,1,1,0,0,0,1,0],
    [0,0,0,0,1,1,0,0,1,0,0],
    [0,0,0,0,1,1,0,1,0,0,0],
    [0,0,1,0,1,1,0,0,0,0,0],
    [0,1,0,0,1,1,0,0,0,0,0],
    [1,0,0,0,1,1,0,0,0,0,0],
    [0,0,0,0,1,1,0,0,0,1,1],
    [0,0,0,0,1,1,0,0,1,1,1],
    [0,0,0,0,1,1,0,1,1,1,0],
    [0,0,0,0,1,1,1,1,1,0,0],
    [0,0,0,0,1,1,1,1,0,0,0],
    [0,0,0,1,1,1,1,0,0,0,0],
    [0,0,1,1,1,1,0,0,0,0,0],
    [0,1,1,1,1,1,0,0,0,0,0],
    [1,1,1,0,1,1,0,0,0,0,0],
    [1,1,0,0,1,1,0,0,0,0,0],
    [0,0,0,0,1,1,0,1,1,1,1],
    [0,0,0,0,1,1,1,1,1,1,0],
    [0,0,0,0,1,1,1,1,1,0,0],
    [0,0,0,1,1,1,1,1,0,0,0],
    [0,0,1,1,1,1,1,0,0,0,0],
    [0,1,1,1,1,1,0,0,0,0,0],
    [1,1,1,1,1,1,0,0,0,0,0],
    [0,0,0,1,1,1,0,0,0,0,1],
    [0,0,0,1,1,1,0,0,1,0,0],
    [0,0,0,1,1,1,0,1,1,1,0],
    [0,0,1,0,1,1,1,1,1,0,0],
    [0,0,0,0,1,1,1,0,1,1,1],
    [0,1,0,0,1,1,1,1,1,0,0]
]
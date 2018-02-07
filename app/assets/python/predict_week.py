# -*- coding: utf-8 -*-
"""
・過去の実績値から休日補正値を算出し、それを元に週sumを予測するプログラム
・上の値と、相関から得られた値を元に調整する関数
weeksumに該当月曜日の日付を入力するとnnによる予測値を出力
"""
import datetime as dt
from datetime import date
import numpy as np
import func
import tensorflow as tf

rng = np.random.RandomState(724)
random_state = 1119

class Dense:
    def __init__(self, in_dim, out_dim, function=lambda x: x):
        # Xavier
        self.W = tf.Variable(rng.uniform(
                        low=-np.sqrt(6/(in_dim + out_dim)),
                        high=np.sqrt(6/(in_dim + out_dim)),
                        size=(in_dim, out_dim)
                    ).astype('float32'), name='W')
        self.b = tf.Variable(np.zeros([out_dim]).astype('float32'))
        self.function = function

    def f_prop(self, x):
        return self.function(tf.matmul(x, self.W) + self.b)


def weeksum(predict_day, predict_week_num=1, name="F"):
    idou_week_n = 5
    kaiki_week_n = 15
    mid=30

    hosei_rate=None
    trend = func.make_trend_idou(name, idou_week_n, predict_day, hosei_rate)
    dates=trend[0]
    X_pred=[]
    for j in range(len(dates)):
        holi=[]
        target_day=dates[j]
        for k in range(1,12):
            if k==5 or k==6 or func.holiday_hantei(target_day+dt.timedelta(days=k)):
                holi.append(1)
            else:
                holi.append(0)
        X_pred.append(holi)

    #NNの定義
    tf.reset_default_graph()
    layers = [
        Dense(11, mid,tf.nn.sigmoid),
        Dense(mid, 1)
    ]
    
    x = tf.placeholder(tf.float32, [None, 11])
    
    def f_props(layers, x):
        for layer in layers:
            x = layer.f_prop(x)
        return x
    
    y_valid = f_props(layers, x)
    valid=tf.nn.relu(y_valid)
    saver = tf.train.Saver()

    #補正レートの再定義
    sess = tf.Session()
    saver.restore(sess, "./model_"+name+"/model_ckpt")
    hosei_rate=[]
    pred_y = sess.run(valid, feed_dict={x: np.array(X_pred)})
    for j in range(len(dates)):
        target_day=dates[j]
        rate=1+func.special_rate(target_day)
        if sum(X_pred[j])==2:
            pred_y[j]=0
        hosei_rate.append(rate+pred_y[j])
        
    #予測対象のトレンド値の取得
    pred_trend = func.make_trend(name, kaiki_week_n, predict_day, predict_week_num, rate=hosei_rate)
    trend_num=pred_trend[2][-1]
    #予測対象の補正値の取得
    hosei_rate = []
    pred = []
    target_day = predict_day
    for j in range(predict_week_num):
        rate=1
        holi=[]
        for i in range(1,12):
            if i==5 or i==6 or func.holiday_hantei(target_day+dt.timedelta(days=i)):
                holi.append(1)
            else:
                holi.append(0)
        if sum(holi)!=2:
            rate += sess.run(valid, feed_dict={x: np.array([holi])})[0][0]
        rate += func.special_rate(target_day)
        hosei_rate.append(rate)
        pred.append(trend_num[j]*rate)
        target_day += dt.timedelta(days=7)
    sess.close()
    return trend_num, hosei_rate, pred

#トレンド値とNNによる休日補正による予測値と相関係数による予測値を調整する
def pred_week(predict_day, name="F"):#NN値,補正値,曜日,相関値
    wd=predict_day.weekday()
    target_monday=predict_day-dt.timedelta(days=wd)
    mix_rate=[0.258977993,0.419160883,0.623406712,0.770452391,0.886324529,1]
    num_nn = weeksum(target_monday, 1, name)[2][0]
    num_soukan = func.predict_soukan(predict_day,name)
    if (target_monday.month==12 and target_monday.day>=26 and target_monday.day<=29):
        if (predict_day.month==12 and predict_day.day>=30) or (predict_day.month==1 and predict_day.day<=3):
            return num_soukan[1]
        else:
            return num_nn
    elif target_monday.month==12 and target_monday.day==30:
        if predict_day.month==1 and predict_day.day==4:
            return num_soukan[1]
        else:
            return num_nn
    elif (target_monday.month==12 and target_monday.day==31) or (target_monday.month==1 and target_monday.day<=3):
        if wd==5:
            return num_soukan[0]
        else:
            return num_nn            
#        if (predict_day.month==12 and predict_day.day==31) or (predict_day.month==1 and predict_day.day<=3):
#            return num_nn
#        else:
#            return num_soukan[0]*mix_rate[wd]+num_nn*(1-mix_rate[wd])
    else:
        return num_soukan[0]*mix_rate[wd]+num_nn*(1-mix_rate[wd])
    

if __name__ == "__main__":
    target_day = date(2017, 7, 24)#予測したい週の月曜日を指定
    predict_week_num = 3#何週分一度に予測するかを指定
    pred = weeksum(target_day, predict_week_num, "f")#"f","z","other"
    print(pred)
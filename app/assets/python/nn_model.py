# -*- coding: utf-8 -*-
"""
NNを学習させるプログラム
・事前学習
・逐次学習(←毎週土曜日就業後？に更新)
"""

import func
import datetime as dt
from datetime import date
import numpy as np
import tensorflow as tf
from sklearn.utils import shuffle
import os
import sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

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


def pre_train(predict_day=date(2017, 11, 13), name="F"):
    idou_week_n = 5
    nn_train_num = 100
    n_epochs = 50
    batch_size = 10
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
    t = tf.placeholder(tf.float32, [None, 1])
    
    def f_props(layers, x):
        for layer in layers:
            x = layer.f_prop(x)
        return x
    
    y_valid = f_props(layers, x)
    cost = tf.reduce_mean((t - y_valid)**2)#,axis=0)
    #train = tf.train.GradientDescentOptimizer(0.01).minimize(cost)
    #train = tf.train.GradientDescentOptimizer(0.1).minimize(cost)
    train = tf.train.AdamOptimizer().minimize(cost)
    valid=tf.nn.relu(y_valid)
    saver = tf.train.Saver()

    sess = tf.Session()
#    init = tf.global_variables_initializer()
    init = tf.initialize_all_variables()
    sess.run(init)
    for i in range(nn_train_num):
        #データセットの生成
        trend = func.make_trend_idou(name, idou_week_n, predict_day, hosei_rate)
        dates=trend[0]
        order_num=trend[1]
        trend_num=trend[2]
        X=[]
        y=[]
        for j in range(idou_week_n,len(dates)-idou_week_n):
            target_day=dates[j]
            rate=1.0+func.special_rate(target_day)
            holi=[]
            for k in range(1,12):
                if k==5 or k==6 or func.holiday_hantei(target_day+dt.timedelta(days=k)):
                    holi.append(1)
                else:
                    holi.append(0)
            train_rate=order_num[j]/trend_num[j]-rate
            if abs(train_rate)<0.4 and sum(holi)!=2:
                X.append(holi)
                if train_rate<0:
                    train_rate=0
                y.append(train_rate)
        #学習
        X=np.array(X)
        y=np.array(y).reshape((len(y),1))
        n_batches = X.shape[0]//batch_size
                
        for epoch in range(n_epochs):
            train_X, train_y = shuffle(X, y, random_state=random_state)
            for j in range(n_batches):
                start = j * batch_size
                end = start + batch_size
                _ , train_cost = sess.run([train,cost], feed_dict={x: train_X[start:end], t: train_y[start:end]})
        #補正レートの再定義
        hosei_rate=[]
        pred_y = sess.run(valid, feed_dict={x: np.array(X_pred)})
        for j in range(len(dates)):
            target_day=dates[j]
            rate=1.0+func.special_rate(target_day)
            if sum(X_pred[j])==2:
                pred_y[j]=0
            hosei_rate.append(rate+pred_y[j])
#        test_y = sess.run(valid, feed_dict={x: np.array(func.test_X)})
#        for p,q in zip(func.test_X,test_y):
#            print(p,q)

#    saver.save(sess, "./model/model_ckpt")
    saver.save(sess, "./model_"+name+"/model_ckpt")
    sess.close()

def online_train(predict_day, save_model=True, predict_week_num=1, name="F"):
    idou_week_n = 5
    kaiki_week_n = 10
    nn_train_num = 10
    n_epochs = 10
    batch_size = 10
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
    t = tf.placeholder(tf.float32, [None, 1])
    
    def f_props(layers, x):
        for layer in layers:
            x = layer.f_prop(x)
        return x
    
    y_valid = f_props(layers, x)
    cost = tf.reduce_mean((t - y_valid)**2)#,axis=0)
    #train = tf.train.GradientDescentOptimizer(0.01).minimize(cost)
    #train = tf.train.GradientDescentOptimizer(0.1).minimize(cost)
    train = tf.train.AdamOptimizer().minimize(cost)
    valid=tf.nn.relu(y_valid)
    saver = tf.train.Saver()

    #補正レートの再定義
    sess = tf.Session()
#    saver.restore(sess, "./model/model_ckpt")
    saver.restore(sess, "./model_"+name+"/model_ckpt")
    hosei_rate=[]
    pred_y = sess.run(valid, feed_dict={x: np.array(X_pred)})
    for j in range(len(dates)):
        target_day=dates[j]
        rate=1.0+func.special_rate(target_day)
        if sum(X_pred[j])==2:
            pred_y[j]=0
        hosei_rate.append(rate+pred_y[j])

    for i in range(nn_train_num):
        #データセットの生成
        trend = func.make_trend_idou(name, idou_week_n, predict_day, hosei_rate)
        dates=trend[0]
        order_num=trend[1]
        trend_num=trend[2]
        X=[]
        y=[]
        for j in range(idou_week_n,len(dates)-idou_week_n):
            target_day=dates[j]
            rate=1.0+func.special_rate(target_day)
            holi=[]
            for k in range(1,12):
                if k==5 or k==6 or func.holiday_hantei(target_day+dt.timedelta(days=k)):
                    holi.append(1)
                else:
                    holi.append(0)
            train_rate=order_num[j]/trend_num[j]-rate
            if abs(train_rate)<0.4 and sum(holi)!=2:
                X.append(holi)
                if train_rate<0:
                    train_rate=0
                y.append(train_rate)
        #学習
        X=np.array(X)
        y=np.array(y).reshape((len(y),1))

        n_batches = X.shape[0]//batch_size
                
        for epoch in range(n_epochs):
            train_X, train_y = shuffle(X, y, random_state=random_state)
            for j in range(n_batches):
                start = j * batch_size
                end = start + batch_size
                _ , train_cost = sess.run([train,cost], feed_dict={x: train_X[start:end], t: train_y[start:end]})
        #補正レートの再定義
        hosei_rate=[]
        pred_y = sess.run(valid, feed_dict={x: np.array(X_pred)})
        for j in range(len(dates)):
            target_day=dates[j]
            rate=1.0+func.special_rate(target_day)
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
        rate=1.0
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
    if save_model:
#        saver.save(sess, "./model/model_ckpt")
        saver.save(sess, "./model_"+name+"/model_ckpt")
    sess.close()
    return trend_num, hosei_rate, pred

def nn_test(name):
    mid=30
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
#    saver.restore(sess, "./model/model_ckpt")
    saver.restore(sess, "./model_"+name+"/model_ckpt")
    test_y = sess.run(valid, feed_dict={x: np.array(func.test_X)})
    for p,q in zip(func.test_X,test_y):
        print(p,q)

if __name__ == "__main__":
    names=["f","z","other"]
    args = sys.argv
    if len(args)==4:
        learn_day=date(int(args[1]),int(args[2]),int(args[3]))
    else:
        learn_day=date.today()
    learn_day-=dt.timedelta(days=learn_day.weekday())
    for name in names:
        if not(os.path.exists("model_"+name)):
            os.mkdir("model_"+name)
        pre_train(learn_day,name)
    for name in names:
	    nn_test(name)

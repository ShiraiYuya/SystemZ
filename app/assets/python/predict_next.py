# -*- coding: utf-8 -*-
"""
土曜日の夜～日曜に(1度だけ)実行するもの
・NNを更新する
・翌週以降の予測を出力する
"""
import func
import nn_model
import datetime as dt
from datetime import date
import sys

predict_week_num = 2

def predict_n(target_day=date.today()):
    names=["f","z","other"]
    wd=target_day.weekday()
    if wd>=5:
        target_monday=target_day+dt.timedelta(days=7-wd)
    else:
        target_monday=target_day-dt.timedelta(days=wd)
    next_pred=[]
    #NNの更新と予測値の取得
    for name in names:
        next_pred.append(nn_model.online_train(target_monday, True, predict_week_num, name)[2])
    preds=[]#axis0:n週後、axis1:fzo、axis2:月～土
    for i in range(predict_week_num):
        pred=[]
        max_day=target_monday-dt.timedelta(days=1)+dt.timedelta(days=i*7)
        for j in range(3):
            we = list(func.weeksum_day(max_day, next_pred[j][i], name))
            we.append(0)
            pred.append(we)
        preds.append(pred)
    return preds        
        
        
if __name__ == "__main__":
    args = sys.argv
    if len(args)==4:
        learn_day=date(int(args[1]),int(args[2]),int(args[3]))
    else:
        learn_day=date.today()
#    learn_day=date(2015,12,28)
#    learn_day=date(2017,6,3)
    ans = predict_n(learn_day)
    for i in range(len(ans)):
        print(ans[i])

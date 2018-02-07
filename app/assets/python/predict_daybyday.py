# -*- coding: utf-8 -*-
"""
月曜朝(4時)～金曜朝(4時)に実行すべきもの
予測を更新する
"""
import sys
import datetime as dt
from datetime import date
import mysql.connector
import config
import func
import predict_week


dbcon = mysql.connector.connect(
database=config.db, 
user=config.user, 
password=config.passwd, 
host=config.host,
buffered=True)
dbcur = dbcon.cursor()


def predict_dbd(target_day=date.today()):
    names=["f","z","other"]
    wd=target_day.weekday()
    target_monday=target_day-dt.timedelta(days=wd)
    
    preds=[]
    for name in names:
        #1 該当週の合計量の予測(by NNと相関、土曜日だけは確定値を算出)
        if wd==5:
            col_name=name+"_ship"
            dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE " 
                          "date>=%s AND date<=%s",(target_monday, target_day))
            num_pred = dbcur.fetchone()[0]
            if num_pred is None:
                num_pred = 0
        else:
            num_pred = predict_week.pred_week(target_day, name)
        #2 残り発送量の算出
        col_name=name+"_ship"
        dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE "
                      "date>=%s AND date<=%s",(target_monday, target_day))
        num = dbcur.fetchone()[0]
        if num is None:
            num = 0
        pred=[0 for col in range(wd+1)]
        pred.extend(func.weeksum_day(target_day, num_pred - num, name))
        pred.append(0)
        preds.append(pred)
        print(preds[-1])
    #全種sum(今日の発送量とpredsの発送量の合計 - 作り置き量)
    return preds

        
        
        
if __name__ == "__main__":
    args = sys.argv
    if len(args)==4:
        learn_day=date(int(args[1]),int(args[2]),int(args[3]))
    else:
        learn_day=date.today()
    predict_dbd(learn_day)
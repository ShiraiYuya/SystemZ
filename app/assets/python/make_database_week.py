# -*- coding: utf-8 -*-
"""
amountsを元に新たなtable「week_data」を作成
各一週間について、「月朝4時まで」「火～」～「土朝4時まで」＋「集合計」

Created on Thu Feb 15 19:16:21 2018

@author: Kazuho
"""

import datetime as dt
from datetime import date
import mysql.connector
import config


dbcon = mysql.connector.connect(
database=config.db, 
user=config.user, 
password=config.passwd, 
host=config.host,
buffered=True)
dbcur = dbcon.cursor()

dbcur.execute("CREATE TABLE week_data (id INT PRIMARY KEY AUTO_INCREMENT, monday DATE," 
              "f_0_morn FLOAT(8,3), f_1_morn FLOAT(8,3), f_2_morn FLOAT(8,3), f_3_morn FLOAT(8,3)," 
              "f_4_morn FLOAT(8,3), f_5_morn FLOAT(8,3), f_week FLOAT(8,3)," 
              "z_0_morn FLOAT(8,3), z_1_morn FLOAT(8,3), z_2_morn FLOAT(8,3), z_3_morn FLOAT(8,3)," 
              "z_4_morn FLOAT(8,3), z_5_morn FLOAT(8,3), z_week FLOAT(8,3)," 
              "other_0_morn FLOAT(8,3), other_1_morn FLOAT(8,3), other_2_morn FLOAT(8,3), other_3_morn FLOAT(8,3)," 
              "other_4_morn FLOAT(8,3), other_5_morn FLOAT(8,3), other_week FLOAT(8,3))")

max_day=date(2018, 1, 22)
target_day_f=date(2015, 4, 6)
while target_day_f<max_day:
    weight_each = [0, target_day_f]
    names = ["f","z","other"]
    for name in names:
        for wd in range(6):
            target_day_t = target_day_f+dt.timedelta(days=wd)
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
            weight_each.append(wd_weight_1 + wd_weight_2)
        col_name=name+"_ship"
        dbcur.execute("SELECT SUM("+col_name+") FROM amounts WHERE date>=%s AND date<%s" 
                      ,(target_day_f,target_day_f+dt.timedelta(days=7)))
        total_weight=dbcur.fetchone()[0]
        if total_weight is None:
            total_weight=0
        weight_each.append(total_weight)
    dbcur.execute("INSERT INTO week_data VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s," 
                  "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",weight_each)
    target_day_f += dt.timedelta(days=7)
dbcur.execute("ALTER TABLE week_data ADD INDEX date_index(monday)")

dbcon.commit()
dbcur.close()
dbcon.close()
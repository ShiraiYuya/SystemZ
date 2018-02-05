require 'roo-xls'
require 'open3'


class UsersController < ApplicationController
  def index
	#1→日曜/祝日/エラー(グラフのみ表示)，2→is_defが必要(excelフォームとグラフのみ出現)，
	#3→is_finが必要(excelフォームと表修正フォームとグラフが出現)，4→正常(表とグラフを表示)
	@view_mode = 0
	@noexcelmsg　= ""
	
	#excelを受け取って出荷量（f,z,other別）をDBとpythonに渡す
	if params[:file] != nil
		#formからの情報
		setting_fin = (params[:setting_fin]=='false' ? false : true)
		supposed_date = Date.strptime(params[:supposed_date],'%Y-%m-%d')
		supdate_str = supposed_date.strftime("%m月%d日")
		#excelの取得
		if (params[:file].path.split(".").last != "xls" or
			Roo::Excel.new(params[:file].path).sheets[0] != '出荷台帳（入力順）')
			@noexcelmsg = "正しいエクセルファイルが登録されていません．<br>".html_safe+supdate_str+"のファイルを登録してください．"
			@tabledate = Amount.find_or_create_by(date: supposed_date)
			@view_mode = (setting_fin ? 3 : 2)			
		else
			xls = Roo::Excel.new(params[:file].path)
			xls.default_sheet = '出荷台帳（入力順）'		
			shipdate = Date.strptime(xls.cell(2,3).encode("UTF-8"),'%m/%d ')
			
			if (shipdate.month == supposed_date.month) and (shipdate.day == supposed_date.day)
				
				regist_xls(xls, supposed_date, setting_fin)
				
				if setting_fin
					@tabledate = Amount.find_or_create_by(date: supposed_date)
					@view_mode = 3
					@noexcelmsg = (supdate_str+"の製造量を更新しました．<br>値に間違いがなければ確認ボタンを押してください．").html_safe
				else
					#ここでpythonを実行
					if supposed_date.wday == 6
						@noexcelmsg = regist_py_sat(supposed_date)
					elsif
						@noexcelmsg = regist_py(supposed_date)
					end
					@view_mode = 1 if @noexcelmsg != ""
				end
			else
				@noexcelmsg = "正しいエクセルファイルが登録されていません．<br>".html_safe+supdate_str+"のファイルを登録してください．"
				@tabledate = Amount.find_or_create_by(date: supposed_date)
				@view_mode = (setting_fin ? 3 : 2)
			end
		end
	end
	#ここまでexcel受け取り時の処理
	
	#作り置き製造量の実績値を受け取ってDBに渡す
	#ここでis_fin=trueになる
	if params[:commit] == "確定"
		supposed_date = Date.strptime(params[:supposed_date],'%Y-%m-%d')
		amount = Amount.find_by(date: supposed_date)
		amount.update(f_store: params[:f_result],z_store: params[:z_result], is_fin: true)
		if supposed_date.wday != 6
			amount = Amount.find_by(date: supposed_date.tomorrow)
			amount.update(f_stored: params[:f_result],z_stored: params[:z_result])
		end
	end
	
	
	#本日のデータ取得
	date = Time.zone.today
#	date = DateTime.strptime('2018-01-27','%Y-%m-%d')
	@time = date
	wday = date.wday
	
	if wday == 0
		@noexcelmsg = "本日は日曜日です．"
		@view_mode = 1
	end
	if is_holiday(date)
		@noexcelmsg = "本日は祝日です．"
		@view_mode = 1
	end
	
	
	#情報更新不足の確認
	if @view_mode == 0
		iday = date.ago((wday+1).day)
		amount = Amount.find_or_create_by(date: iday)
		if amount.is_def and !amount.is_fin
			@supposed_date = iday
			supdate_str = iday.strftime("%m月%d日")
			@noexcelmsg = supdate_str+"分の情報を更新してください．"
			@setting_fin = true
			@tabledate = amount
			@view_mode = 3
		end
	end
	
	jwdaylist = ["月曜","火曜","水曜","木曜","金曜","土曜"]
	for i in 1..(wday-1) do
		iday = date.ago(wday.day).since(i.day)
		if @view_mode == 0
			amount = Amount.find_or_create_by(date: iday)
			@supposed_date = iday
			supdate_str = iday.strftime("%m月%d日")
			if !amount.is_def
				@noexcelmsg = supdate_str+"分のエクセルファイルを入力してください．"
				@setting_fin = false
				@tabledate = amount
				@view_mode = 2
			elsif !amount.is_fin
				@noexcelmsg = supdate_str+"分の情報を更新してください．"
				@setting_fin = true
				@tabledate = amount
				@view_mode = 3
			end
		end	
	end
	
	if @view_mode == 0
		amount = Amount.find_or_create_by(date: date)
		if amount.is_def
			@today = amount
			@view_mode = 4
		else
			@supposed_date = date
			@noexcelmsg = "本日分のエクセルファイルを入力してください．"
			@setting_fin = false
			@tabledate = amount
			@view_mode = 2
		end		
	end
	
	#テーブル内の浮動小数点問題解決
	if @view_mode == 3
		@table_f_make = floor_n([(@tabledate.f_ship - @tabledate.f_stored),0].max)
		@table_z_make = floor_n([(@tabledate.z_ship - @tabledate.z_stored),0].max)
		@table_other_make = floor_n(@tabledate.other_ship)
		@table_all_make = floor_n([(@tabledate.f_ship - @tabledate.f_stored),0].max + [(@tabledate.z_ship - @tabledate.z_stored),0].max + @tabledate.other_ship)
		@table_f_premake = floor_n(@tabledate.f_store)
		@table_z_premake = floor_n(@tabledate.z_store)
		@table_all_premake = floor_n(@tabledate.f_store + @tabledate.z_store)
		
	end
	
	if @view_mode == 4
		@today_f_ship = floor_n(@today.f_ship)
		@today_z_ship = floor_n(@today.z_ship)
		@today_other_ship = floor_n(@today.other_ship)
		@today_all_ship = floor_n(@today.f_ship + @today.z_ship + @today.other_ship)
		
		@today_f_stored = floor_n(@today.f_stored)
		@today_z_stored = floor_n(@today.z_stored)
		@today_all_stored = floor_n(@today.f_stored + @today.z_stored)
		
		@today_f_store = floor_n(@today.f_store)
		@today_z_store = floor_n(@today.z_store)
		@today_all_store = floor_n(@today.f_store + @today.z_store)
		
		@today_f_make = floor_n([(@today.f_ship - @today.f_stored),0].max)
		@today_z_make = floor_n([(@today.z_ship - @today.z_stored),0].max)
		@today_all_make = floor_n([(@today.f_ship - @today.f_stored + @today.z_ship - @today.z_stored + @today.other_ship),0].max)

		
		@today_f_summake = floor_n([(@today.f_ship - @today.f_stored + @today.f_store),0].max)
		@today_z_summake = floor_n([(@today.z_ship - @today.z_stored + @today.z_store),0].max)
		@today_all_summake = floor_n([(@today.f_ship - @today.f_stored + @today.f_store + @today.z_ship - @today.z_stored + @today.z_store + @today.other_ship),0].max)
		
		@today_f_ratio = floor_n([(@today.f_ship - @today.f_stored + @today.f_store),0].max / @today.f_ship )
		@today_z_ratio = floor_n([(@today.z_ship - @today.z_stored + @today.z_store),0].max / @today.z_ship )
		@today_other_ratio = "1.00"
		@today_all_ratio = floor_n([(@today.f_ship - @today.f_stored + @today.f_store + @today.z_ship - @today.z_stored + @today.z_store + @today.other_ship),0].max / (@today.f_ship + @today.z_ship + @today.other_ship) )
	end
	
	view_graph(date)
  end

  def conf
	@products = Product.where(company: 1)
	@materials = Material.where(company: 1)
  end

  def stock
  end
  
  def floor_n(float)
#	return BigDecimal(float.to_s).floor(2).to_f
	return sprintf("%#.2f", float)
  end
  
  def regist_xls(xls, shipdate, setting_fin)
	swday = shipdate.wday
		
	#出荷量の算出
	f,zenran,other = 0,0,0
	for i in 4..xls.last_row do
		#sizeやnumのところに数値がないとバグりそう
		if xls.cell(i, 4) != nil
			product = xls.cell(i, 4).encode("UTF-8")
			size = xls.cell(i, 6).tr!("０-９", "0-9").to_i
			num = xls.cell(i, 10).tr!("０-９", "0-9").to_i

			if product=="Ｆ"
				f += size * num
			elsif product=="全卵"
				zenran += size * num 
			else
				other += size * num
			end				
		end
	end
	#kg変換
	f /= 1000
	zenran /= 1000
	other /= 1000 
		
	#ここでDBに登録
	#初回:shipに加えmornも登録(このあとpython計算上手くいけばis_def=trueになる)
	#２回目以降:shipのみ更新　→　現状ここは存在しないが・・・
	#最後（翌日）:is_fin→true,ship更新
	amount = Amount.find_or_create_by(date: shipdate)
	if amount.is_def
		amount.update(f_ship: f, z_ship: zenran, other_ship: other)
	else
		amount.update(f_ship: f, f_morn: f, z_ship: zenran,z_morn: zenran, other_ship: other, other_morn: other)
	end	
  end
  
  def is_holiday(date)
	day_s = date.strftime("%m/%d")
	if (day_s == "12/31" or day_s == "01/01" or day_s =="01/02" or day_s == "01/03")
		return(true)
	else
		return(false)
	end
  end
  
  def regist_py(shipdate)
	swday = shipdate.wday
	
	#python実行，返り値の受け取り
	sdstring = shipdate.strftime("%Y %m %d")
	out, err, status = Open3.capture3("cd app/assets/python;"+"python predict_daybyday.py "+sdstring+";"+"cd ../../../;", :stdin_data=>"foo\nbar\nbaz\n")
	out = out.gsub(/(\n|\[)/,"").gsub(/(\])/,",").split(",")
	out = out.map(&:to_f)
	return(status) if err != ""
	return(out.to_s) if out.length != 21
	
	#受け取りは各日の予測出荷量（f,z,other別）：月から日まで
	amount = Amount.find_by(date: shipdate)
	f_py = out[0..6]
	z_py = out[7..13]
	other_py = out[14..20]
	
	#shipdate~土までに作る総量sum（f,z,other別），平均averを算出
	f_sum = amount.f_ship - amount.f_stored + f_py.sum
	z_sum = amount.z_ship - amount.z_stored + z_py.sum
	other_sum = amount.other_ship + other_py.sum
	sum = f_sum + z_sum + other_sum
	
	day_remain = f_py[swday..-1].length - f_py[swday..-1].count(0) + 1
	aver = (sum / day_remain).to_i		
	
	#shipdateのstore登録（f,z別）
	store = [aver - (amount.f_ship - amount.f_stored) - (amount.z_ship - amount.z_stored) - amount.other_ship, 0].max
	f_store = (-z_sum * (amount.f_ship - amount.f_stored) + f_sum * (amount.z_ship - amount.z_stored + store)) / (z_sum + f_sum)
	f_store = [[f_store,store,f_py[swday]].min, 0].max
	z_store = [store - f_store, z_py[swday]].min
	f_store = z_store = 0 if is_holiday(shipdate)
	store = f_store + z_store
	#ここでis_def=trueになる
	amount.update(f_store: f_store, z_store: z_store, is_def: true)
	
	#sumの更新
	sum -= (amount.f_ship - amount.f_stored + amount.f_store) + (amount.z_ship - amount.z_stored + amount.z_store) + amount.other_ship
	f_sum -= amount.f_ship - amount.f_stored + amount.f_store
	z_sum -= amount.z_ship - amount.z_stored + amount.z_store
	
	#shipdateの次の日以降のship(予測),stored,store登録
	for i in (swday+1)..6 do
		#stored,shipの更新
		day_remain = f_py[(i-1)..-1].length - f_py[(i-1)..-1].count(0)
		day_remain = 1 if day_remain == 0
		aver = sum / day_remain
		amount = Amount.find_or_create_by(date: shipdate.ago(swday.day).since(i.day))
		amount.update(f_stored: f_store, z_stored: z_store, f_ship: f_py[i-1] , z_ship: z_py[i-1], other_ship: other_py[i-1])
		amount.update(is_def: true, is_fin: true) if is_holiday(amount.date)
		
		#storeの計算，更新
		store = [aver - (f_py[i-1] + z_py[i-1] + other_py[i-1] - store), 0].max
		f_store = (-z_sum * (f_py[i-1] - f_store) + f_sum * (z_py[i-1] - z_store + store) ) / (z_sum + f_sum)
		f_store = [[f_store,store,f_py[i]].min, 0].max
		z_store = [store - f_store, z_py[i]].min
		f_store = z_store = 0 if is_holiday(amount.date)
		store = f_store + z_store
		amount.update(f_store: f_store, z_store: z_store)
		
		#sumの更新
		sum -= (amount.f_ship - amount.f_stored + amount.f_store) + (amount.z_ship - amount.z_stored + amount.z_store) + amount.other_ship
		f_sum -= amount.f_ship - amount.f_stored + amount.f_store
		z_sum -= amount.z_ship - amount.z_stored + amount.z_store
	end
	return("")
  end
  
  
  def regist_py_sat(shipdate)
	#python実行，返り値の受け取り
	swday = shipdate.wday
	sdstring = shipdate.strftime("%Y %m %d")
	out, err, status = Open3.capture3("cd app/assets/python;"+"python predict_next.py "+sdstring+";"+"cd ../../../;", :stdin_data=>"foo\nbar\nbaz\n")
	out = out.gsub(/(\]\])/,",").gsub(/(\n|\[|\])/,"").split(",")
	out = out.map(&:to_i)
	return(err) if err != ""
	return(out.to_s) if out.length != 42
	
	amount = Amount.find_by(date: shipdate)
	amount.update(is_def: true)
	
	#j=0は翌週分，j=1は翌々週分	
	for j in 0..1
		f_nw_py = out[(j*21)..(j*21+6)]
		z_nw_py = out[(j*21+7)..(j*21+13)]
		other_nw_py = out[(j*21+14)..(j*21+20)]
	
		#翌週月~土までに作る総量sum（f,z,other別），平均averを算出
		f_sum = f_nw_py.sum
		z_sum = z_nw_py.sum
		other_sum = other_nw_py.sum
		sum = f_sum + z_sum + other_sum
		f_store = 0
		z_store = 0
		store = 0
	
		#その週の各日のship(予測),stored,store登録
		for i in 1..6 do
			#stored,shipの更新
			day_remain = f_nw_py[(i-1)..-1].length - f_nw_py[(i-1)..-1].count(0)
			day_remain = 1 if day_remain == 0
			aver = sum / day_remain
			amount = Amount.find_or_create_by(date: shipdate.since((j*7+1+i).day))
			amount.update(f_stored: f_store, z_stored: z_store, f_ship: f_nw_py[i-1] , z_ship: z_nw_py[i-1], other_ship: other_nw_py[i-1])
			amount.update(is_def: true, is_fin: true) if is_holiday(amount.date)
			
			#storeの計算，更新
			store = [aver - (f_nw_py[i-1] + z_nw_py[i-1] + other_nw_py[i-1] - store), 0].max
			f_store = (-z_sum * (f_nw_py[i-1] - f_store) + f_sum * (z_nw_py[i-1] - z_store + store) ) / (z_sum + f_sum)
			f_store = [[f_store,store,f_nw_py[i]].min, 0].max
			z_store = [store - f_store, z_nw_py[i]].min
			f_store = z_store = 0 if is_holiday(amount.date)
			store = f_store + z_store
			amount.update(f_store: f_store, z_store: z_store)
			
			#sumの更新
			sum -= (amount.f_ship - amount.f_stored + amount.f_store) + (amount.z_ship - amount.z_stored + amount.z_store) + amount.other_ship
			f_sum -= amount.f_ship - amount.f_stored + amount.f_store
			z_sum -= amount.z_ship - amount.z_stored + amount.z_store
		end
	end
	return("")
  end
  
  
  def view_graph(date)
	wday = date.wday
	
	#グラフ用データ
	wdaylist = ["月","火","水","木","金","土"]

	f_ship_list = [] #出荷
	f_make_list = [] #製造
	f_makepred_list = [] #製造（予測）
	f_store_list = [] #保存
	f_pred_list = [] #出荷（予測）
	z_ship_list = []
	z_make_list = []
	z_makepred_list = []
	z_store_list = []
	z_pred_list = []
	other_ship_list = []
	other_pred_list = []
	
	for i in 1..6 do
		if Amount.exists?(:date => date.ago(wday.day).since(i.day))
			amount = Amount.find_by(date: date.ago(wday.day).since(i.day))
			if amount.is_def
				f_ship_list.push([wdaylist[i-1],amount.f_ship])
				z_ship_list.push([wdaylist[i-1],amount.z_ship])
				other_ship_list.push([wdaylist[i-1],amount.other_ship])
				f_make_list.push([wdaylist[i-1],amount.f_ship-amount.f_stored]) if amount.f_ship-amount.f_stored>0
				z_make_list.push([wdaylist[i-1],amount.z_ship-amount.z_stored]) if amount.z_ship-amount.z_stored>0
			else
				f_pred_list.push([wdaylist[i-1],amount.f_ship])
				z_pred_list.push([wdaylist[i-1],amount.z_ship])
				other_pred_list.push([wdaylist[i-1],amount.other_ship])
				f_makepred_list.push([wdaylist[i-1],amount.f_ship-amount.f_stored]) if amount.f_ship-amount.f_stored>0
				z_makepred_list.push([wdaylist[i-1],amount.z_ship-amount.z_stored]) if amount.z_ship-amount.z_stored>0
			end
			f_store_list.push([wdaylist[i-1],amount.f_store])
			z_store_list.push([wdaylist[i-1],amount.z_store])
			max_ship1 = amount.f_ship + amount.z_ship + amount.other_ship if i==6
		end
	end
	
	
	#翌週分
	f_makepred_nw_list = [] #製造（予測）
	f_store_nw_list = [] #保存
	f_pred_nw_list = [] #出荷（予測）
	z_makepred_nw_list = []
	z_store_nw_list = []
	z_pred_nw_list = []
	other_pred_nw_list = []
	
	for i in 1..6 do
		if Amount.exists?(:date => date.ago(wday.day).since((7+i).day))
			amount = Amount.find_by(date: date.ago(wday.day).since((7+i).day))
			f_pred_nw_list.push([wdaylist[i-1],amount.f_ship])
			z_pred_nw_list.push([wdaylist[i-1],amount.z_ship])
			other_pred_nw_list.push([wdaylist[i-1],amount.other_ship])
			f_makepred_nw_list.push([wdaylist[i-1],amount.f_ship-amount.f_stored]) if amount.f_ship-amount.f_stored>0
			z_makepred_nw_list.push([wdaylist[i-1],amount.z_ship-amount.z_stored]) if amount.z_ship-amount.z_stored>0
			f_store_nw_list.push([wdaylist[i-1],amount.f_store])
			z_store_nw_list.push([wdaylist[i-1],amount.z_store])
			max_ship2 = amount.f_ship + amount.z_ship + amount.other_ship if i==6
		end
	end
	
	max_ship1 = 0 if max_ship1.nil?
	max_ship2 = 0 if max_ship2.nil?
	@max_ship = [max_ship1, max_ship2].max
	
	@chart_data = [
	{name:"None",data:[["月",0],["火",0],["水",0],["木",0],["金",0],["土",0]]},
	{name:"F確定",data:f_make_list},
	{name:"F予測",data:f_makepred_list},
	{name:"F作り置き",data:f_store_list},
	{name:"全卵確定",data:z_make_list},
	{name:"全卵予測",data:z_makepred_list},
	{name:"全卵作り置き",data:z_store_list},
	{name:"その他確定",data:other_ship_list},
	{name:"その他予測",data:other_pred_list}
	]
	
	@chart_data2 = [
	{name:"None",data:[["月",0],["火",0],["水",0],["木",0],["金",0],["土",0]]},
	{name:"F確定",data:f_ship_list},
	{name:"全卵確定",data:z_ship_list},
	{name:"その他確定",data:other_ship_list},
	{name:"F予測",data:f_pred_list},
	{name:"全卵予測",data:z_pred_list},
	{name:"その他予測",data:other_pred_list}
	]
	
	@chart_data3 = [
	{name:"None",data:[["月",0],["火",0],["水",0],["木",0],["金",0],["土",0]]},
	{name:"F予測",data:f_makepred_nw_list},
	{name:"F作り置き",data:f_store_nw_list},
	{name:"全卵予測",data:z_makepred_nw_list},
	{name:"全卵作り置き",data:z_store_nw_list},
	{name:"その他予測",data:other_pred_nw_list}
	]
	
	@chart_data4 = [
	{name:"None",data:[["月",0],["火",0],["水",0],["木",0],["金",0],["土",0]]},
	{name:"F予測",data:f_pred_nw_list},
	{name:"全卵予測",data:z_pred_nw_list},
	{name:"その他予測",data:other_pred_nw_list}
	]
  end
  
end

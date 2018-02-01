class CreateAmounts < ActiveRecord::Migration[5.1]
  def change
    create_table :amounts do |t|
	  t.date	:date
	  t.float	:f_ship, default: 0
	  t.float	:f_stored, default: 0
	  t.float	:f_store, default: 0
	  t.float	:f_morn, default: 0
	  t.float	:z_ship, default: 0
	  t.float	:z_stored, default: 0
	  t.float	:z_store, default: 0
	  t.float	:z_morn, default: 0
	  t.float	:other_ship, default: 0
	  t.float	:other_morn, default: 0
	  t.boolean	:is_def, default: false
	  t.boolean	:is_fin, default: false
	  
      t.timestamps
    end
  end
end

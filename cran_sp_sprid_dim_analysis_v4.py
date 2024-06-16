# -*- coding: utf-8 -*-
"""
Created on Tue Aug  4 15:04:11 2020

"""
# Cran SP Sprid Dims Analysis

# import libraries
import pandas as pd
import numpy as np
import itertools
#import math


import datetime
starttime = datetime.datetime.now()

# Part 1: Create a list of rack dims
d1 = [33]
d2 = list(range(42, 48+ 1,1))
d3 = list(range(60, 66+ 1,1))
#depth = [42, 32, 60] # test 42 only
depth = d1 + d2 + d3

width_max = 60
width = list(range(8, width_max + 1,1)) # from 8 to 60 with 1 inch incremental

height_max = 60
height = list(range(3, height_max + 1,1)) # from 3 to 60 with 1 inch incremental

# set list to drop duplicates
rack_dims = list(set([( str(max(d,w,h)) + 'x' + str(d+w+h - max(d,w,h) - min(d,w,h)) + 'x' + str(min(d,w,h)), 
                  max(d,w,h), d+w+h - max(d,w,h) - min(d,w,h), min(d,w,h)) for d, w, h in itertools.product(depth, width, height)]))
#len(rack)
rack_dims = pd.DataFrame(rack_dims, columns = ['Rack_Dims', 'MaxDim', 'MidDim', 'MinDim']) 
      
       
# Part 2: Sprid dims data
sprid_dims = pd.read_csv(r'C:\Users\SQL\Sprid_Profile\cran_sp_distinct_dims.csv')
sprid_dims['cube'] = sprid_dims['units'] * sprid_dims['MaxDim'] * sprid_dims['MidDim'] * sprid_dims['MinDim'] / 1728

sprid_dims.rename(columns = {'MaxDim': 'Sprid_MaxDim','MidDim': 'Sprid_MidDim','MinDim':'Sprid_MinDim'}, inplace = True)
sprid_dims['Sprid_Dims'] = sprid_dims['Sprid_MaxDim'].astype(str) + 'x'+ sprid_dims['Sprid_MidDim'].astype(str) +'x' + sprid_dims['Sprid_MinDim'].astype(str) 

sprid_dims = sprid_dims[['Sprid_MaxDim','Sprid_MidDim','Sprid_MinDim','Sprid_Dims','units']]
sprid_dims = sprid_dims.drop_duplicates().reset_index(drop = True)


# Part 3: df list
rack_list = rack_dims['Rack_Dims'].unique()
sprid_list = sprid_dims['Sprid_Dims'].unique()

comb = [(i,j) for i, j in itertools.product(rack_list, sprid_list)]

df_comb = pd.DataFrame(comb, columns = ['Rack_Dims','Sprid_Dims'])

df = pd.merge(df_comb, rack_dims, on = ['Rack_Dims'] , how = 'outer')
df = pd.merge(df, sprid_dims, on = ['Sprid_Dims'] , how = 'outer')


   

# Part 4: Caculation
# sprid cube and rack cube
df['Sprid_cube'] = df['Sprid_MaxDim'] * df['Sprid_MidDim'] * df['Sprid_MinDim'] / 1728
df['Rack_cube'] = df['MaxDim'] * df['MidDim'] * df['MinDim'] / 1728

# num of units per location as factor (f)
unit_threshold = 4

df['f'] = np.minimum(unit_threshold
  , np.floor(df['MaxDim'] / df['Sprid_MaxDim'])
  * np.floor(df['MidDim'] / df['Sprid_MidDim'])
  * np.floor(df['MinDim'] / df['Sprid_MinDim'])
  )

# cube loss based on criteria
# filter by condition
df1 = df[(df['MaxDim'] >= df['Sprid_MaxDim']) & (df['MidDim'] >= df['Sprid_MidDim']) & (df['MinDim'] >= df['Sprid_MinDim'])]
df2 = df[(df['MaxDim'] < df['Sprid_MaxDim']) | (df['MidDim'] < df['Sprid_MidDim']) | (df['MinDim'] < df['Sprid_MinDim'])]

# calculate for df1 
df1['cube_loss'] = np.minimum(0, df1['units'] / df1['f'] * (df1['f'] * df1['Sprid_cube'] - df1['Rack_cube']))
df1['eff_units'] = df1['units']
df1['eff_cube'] = df1['units'] * df1['Sprid_cube']
df1['cube_fill_rate'] = df1['f'] * df1['Sprid_cube'] / df1['Rack_cube']
df1.reset_index(drop = True, inplace = True)


# calculate for df2
df2['cube_loss'] = -1 * df2['units'] * df2['Sprid_cube']
df2['eff_units'] = 0
df2['eff_cube'] = 0
df2['cube_fill_rate'] = 0
df2.reset_index(drop = True, inplace = True)

df_new = pd.concat([df1, df2]).reset_index(drop = True)



# Part 5: find units and cube % by target fill rate
target = 0.8


def calc_pt(df_test):
     
    df_test['cube_pct'] = df_test['Sprid_cube'].transform(lambda x: x/x.sum())
    df_test['units_pct'] = df_test['units'].transform(lambda x: x/x.sum()) # using units, eff_units doesn't have the current sum
    
    df_test = df_test[df_test['cube_fill_rate'] >= target].reset_index(drop = True)

    Rack_Dims = df_test['Rack_Dims'].unique().tolist()
    cube = df_test['Sprid_cube'].sum()
    units = df_test['units'].sum()
    cube_pct = df_test['cube_pct'].sum()
    units_pct = df_test['units_pct'].sum()
    
    output = (Rack_Dims, target, cube, units, cube_pct, units_pct)
    
    return output


# loop over rack dims

rows = []

for group in  df_new.groupby(['Rack_Dims']):

    df_group = pd.DataFrame(group[1]).reset_index(drop = True)
    row = list(calc_pt(df_group))
    
    rows.append(row)
  
#    print(group)

df_final = pd.DataFrame(rows, columns = ['Rack_Dims','target','cube','unit','cube_pct','units_pct'])


endtime = datetime.datetime.now()
print (endtime - starttime)


## print to csv
df_final.to_csv(r'C:\Users\SQL\Sprid_Profile\scenario\4_80\df_final.csv')
#
#df_test = df_new[df_new['Rack_Dims'] == '42x19x18'].reset_index(drop = True)
#df_test.to_csv(r'C:\Users\SQL\Sprid_Profile\scenario\4_80e\df_test.csv')
#
min_loss = df_new.groupby(['Rack_Dims']).sum().reset_index()
min_loss = min_loss[['Rack_Dims','cube_loss','eff_units','eff_cube']].sort_values()
##min_loss.columns
min_loss.to_csv(r'C:\Users\SQL\Sprid_Profile\scenario\4_80\min_loss.csv')


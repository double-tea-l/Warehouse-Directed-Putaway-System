# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 06:42:05 2020

"""

# Import OPL and PPL Init Data

"""
    This code run sql version of OPL and PPL init snapshots and import as data inputs for the consolidation tool.
    The code is refreshed every python run. 
"""

import pypyodbc
import pandas as pd

## source path
#root = r'C:\Users\SQL\Sprid_Profile\consolidation_tool\code'
#
#opl_oh = 'opl_on_hand_snapshot_sql.sql'
#ppl_oh = 'ppl_on_hand_snapshot_sql.sql'
#
#
## Run today's data and append to last data file
#def snapshot(df):
#                               
#    amc =  open("%s/%s"%(root, df), 'r')              
#    query = amc.read()                         
#    conn_string = "Driver={SQL Server Native client 11.0};Server=SQLHIGHJUMPRO;Database=master;Trusted_Connection=yes;"   
#    conn = pypyodbc.connect(conn_string)  
#    print('Reading the query.')
#    data = pd.read_sql(query, conn)            
#    print(df + ' ' + 'is completed.')
#    
#    return data
#    
## import table from sql connection
#opl = snapshot(opl_oh)
#ppl = snapshot(ppl_oh)
#
#
## rename column names because sql returns all names in lower case
#opl.rename(columns = {'run_time': 'Run_time', 'whid':'WHID', 'rack_type':'Rack_Type', 'location_id':'Location_ID'
#                      , 'liquid_cube':'Liquid_Cube','utilization': 'Utilization', 'sprid':'Sprid', 'sprid_cube':'Sprid_Cube'
#                      , 'sprid_units':'Sprid_Units', 'maxdim':'MaxDim', 'middim':'MidDim', 'mindim':'MinDim', 'sprid_dims':'Sprid_Dims'}, inplace = True)
#
#
#ppl.rename(columns = {'run_time': 'Run_time', 'whid':'WHID', 'location_id':'Location_ID', 'rack_dims':'Rack_Dims', 
#                          'depth':'Depth', 'width':'Width','height':'Height'
#                      , 'liquid_cube':'Liquid_Cube','utilization': 'Utilization', 'sprid':'Sprid', 'sprid_cube':'Sprid_Cube'
#                      , 'sprid_units':'OH_Units', 'maxdim':'MaxDim', 'middim':'MidDim', 'mindim':'MinDim', 'sprid_dims':'Sprid_Dims'}, inplace = True)
#
#    
## redefine column data type as necessary
#opl['WHID'] = opl['WHID'].astype(int)
#ppl['WHID'] = ppl['WHID'].astype(int)
#opl['Run_time'] = opl['Run_time'].astype(str)
#ppl['Run_time'] = ppl['Run_time'].astype(str)



opl = pd.read_csv(r'C:\Users\SQL\Sprid_Profile\consolidation_tool\snapshots\init\opl_init.csv', index_col = False)
ppl = pd.read_csv(r'C:\Users\SQL\Sprid_Profile\consolidation_tool\snapshots\init\ppl_init.csv', index_col = False)
#.drop(['Unnamed: 0'],axis=1)

ppl.rename(columns = {'Sprid_Units':'OH_Units'}, inplace = True)


# exclude incorrect dims sprid
exclusion = ['TKCL3472.17389714', 'KD2260.14386703'
             ,'FV48676.7480854','TINS1153.44942805','WLK1921.32224395','UBGK1068.36142649','HAZE1712.12770886'
             ,'SBFT1516.14599340','NTC1160.4468403','KUI5489.8099627','HDNN1008.31337120','PU7132.23931690','BPMT1003.6601922']
opl = opl[~opl['Sprid'].isin(exclusion)].reset_index(drop = True)

# drop ppl location which has multiple sprid on hand
exclude_location = ppl[ppl['num_of_loc_id'] != 1]['Location_ID'].unique()
ppl = ppl[~ppl['Location_ID'].isin(exclude_location)].reset_index(drop = True)
ppl.drop(columns = ['num_of_loc_id'], inplace = True)


## save results to csv as a backup
#opl.to_csv(r'C:\Users\SQL\Sprid_Profile\consolidation_tool\snapshots\init\opl_init.csv')
#ppl.to_csv(r'C:\Users\SQL\Sprid_Profile\consolidation_tool\snapshots\init\ppl_init.csv')
            

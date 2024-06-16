# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 19:27:50 2020

"""

import pandas as pd
from itertools import permutations
from collections import defaultdict
import numpy as np
import math
import sprid_dims
from google.cloud import bigquery
import datetime

"""
    Script populated with convenience functions 
"""


def best_sprid_cand(rack_dims, r1, inc, f) -> pd.DataFrame():
    
    """
    Generate best fit sprid candidate list for ppl
    :param rack_dims: distinct rack dim list from ppl list, e.g.42x21x20
    :param r1: bin fill threshold
    :param inc: rack dim incremental
    :param f: max num of units per location
    :return: sprid candidates that give a >= r1 bin fill rate at max of f units/loc
    """
    
    df_sprid = pd.DataFrame()
    for i in rack_dims:
        D_r = int(i[0:2])
        W_r = int(i[3:5])
        H_r = int(i[6:8])
        
        s1 = sprid_dims.best_fit_sprid_list(D_r, W_r, H_r, r1, inc, f)
        df_sprid_tmp = s1.df_sprid
        df_sprid = pd.concat([df_sprid, df_sprid_tmp])
    
    return df_sprid


def calc(D_r, W_r, H_r, MaxDim, MidDim, MinDim):
    
    """
    Calculate max num of units can fit per location based on Sprid dims and Rack dims
    :param D_r, W_r, H_r: depth, width and height of a rack
    :param MaxDim, MidDim, MinDim: max, mid and min dim of a sprid
    :return f: max num of units per location
    """
    if MaxDim * MidDim * MinDim == 0:
        
        f = 999 # for empty locations which have null sprid with 0 dims on hand, set max to default 999
        
    else: 
        p = list(permutations([MaxDim, MidDim, MinDim], 3))   
                
        deep = [min(math.floor(D_r / i[0]), 1) for i in p]  # no double deep
        col = [math.floor(W_r / i[1]) for i in p]
        level = [math.floor(H_r / i[2]) for i in p]
                        
        comb = [ d*c*l for d, c, l in zip(deep, col, level)]
        f = np.max(comb)
                    
    return f


def recalc_opl_sprid(pick_list, opl_sprid):
    
    """
    Recalculate opl on hand sprid units after picking and delete empty locations
    :param pick_list: pick from locations and sprid units
    :param opl_sprid: opl on hand sprid and units before picking
    :return: refreshed opl_sprid list
    """
#    opl_sprid = cand_opl_sprid    
    df = pd.DataFrame()
    if not pick_list.empty:
        
        df_pick_list = pick_list[['WHID', 'Rack_Type', 'Pick_From', 'Sprid', 'Pick_Sprid_Units']].drop_duplicates()
        df_pick_list.rename(columns = {'Pick_From':'Location_ID'}, inplace = True)
        
        df = pd.merge(opl_sprid, df_pick_list, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left')
        df['Pick_Sprid_Units'].fillna(0, inplace = True)
        df['Sprid_Units'] = df['Sprid_Units'] - df['Pick_Sprid_Units'] 
        df.drop(columns=['Pick_Sprid_Units'], inplace = True)

    else:
#        print('pick list is empty')
        df = opl_sprid
        pass
    
    return df


def recalc_opl_huid(pick_list, opl_huid):
    
    """
    Recalculate opl on hand huid units after picking and delete empty locations
    :param pick_list: pick from locations and huid units
    :param opl_sprid: opl on hand huid and units before picking
    :return: refreshed opl_huid list
    """
    df = pd.DataFrame()
    if not pick_list.empty:
        
        df_pick_list = pick_list[['WHID', 'Rack_Type', 'Pick_From', 'Sprid', 'hu_id', 'Pick_huid_units']].drop_duplicates()
        df_pick_list.rename(columns = {'Pick_From':'Location_ID'}, inplace = True)
        
        df = pd.merge(opl_huid, df_pick_list, on = ['WHID','Rack_Type','Location_ID','Sprid', 'hu_id'], how = 'left')
        df['Pick_huid_units'].fillna(0, inplace = True)
        df['huid_units'] = df['huid_units'] - df['Pick_huid_units'] 
        df.drop(columns=['Pick_huid_units'], inplace = True)

    else:
#        print('pick list is empty')
        df = opl_huid
        pass

    return df


def recalc_ppl_pf(pick_list, ppl_pf):
    
    """
    Recalculate ppl partially full locations after picking and append new pf from empty list if any
    :param pick_list: pick from locations and huid units
    :param ppl_pf: ppl_pf huid and units before picking
    :return: refreshed ppl_pf list
    """
    df = pd.DataFrame()
    if not pick_list.empty:
        if not ppl_pf.empty:
            pick_list = pick_list[pick_list['Excess'] == 0] # non excess units mean pick to are ppl locations
            
            df_pick_to = pd.DataFrame(pick_list.groupby(['WHID', 'Pick_To', 'Sprid'])['Pick_huid_units'].sum().reset_index())
            df_pick_to.rename(columns = {'Pick_To':'Location_ID'}, inplace = True)
            
            df = pd.merge(ppl_pf, df_pick_to, on = ['WHID','Location_ID', 'Sprid'], how = 'left')
            df['Pick_huid_units'].fillna(0, inplace = True)
        
            # recalc on hand units and utilization
            df['OH_Units'] = df['OH_Units'] + df['Pick_huid_units'] 
            df['Utilization'] = df['OH_Units'] * df['Sprid_Cube'] / df['Liquid_Cube'] 
            
            df.drop(columns=['Pick_huid_units'], inplace = True)
            df['u'] = df['f'] - df['OH_Units']
            
        else:
#            print('ppl_pf is empty')
            df = ppl_pf
            pass
    else:
#        print('pick list is empty')
        df = ppl_pf
        pass

    return df


def comb(opl_sprid_cand, u):
    
    """
    Identify if there's any combination of on hand opl locations that gives the exact num of u
    :param opl_sprid_cand: all on hand sprid units of opl locations
    :param u: units required to fill ppl location
    :return: 0/1 to indicate if there's any combindation or not
    """
    df = pd.DataFrame()
    opl_sprid_cand = opl_sprid_cand.sort_values(by = ['Utilization','Location_ID'], ascending = True).reset_index(drop = True)

    nums = opl_sprid_cand['Sprid_Units'].to_list()    
    l = len(nums)
    target = u

    def subset_sum(nums, target, l, partial = [], index = [], result = defaultdict(list)):

        s = sum(partial)

        if s == target:
            result['partial'].append(partial)
            result['index'].append(index)
        if s >= target:
            return
        
        for i in range(len(nums)):

            n = nums[i]
            remaining = nums[i + 1:]
            m = l - len(remaining) - 1
            subset_sum(remaining, target, l, partial + [n], index + [m])
            
        return result

    result = subset_sum(nums, target, l, partial = [], index = [])

    df = pd.DataFrame(result)
    
    if not df.empty:
        comb = 1
    else:
        comb = 0
        
    return comb


def recalc_ppl_empty(pick_list, ppl_empty):
    
    """
    Recalculate ppl empty locations
    :param pick_list: pick to column will indicate if it's an empty location
    :ppl_empty: ppl empty locations before putting
    :return: ppl empty locations after putting, some will become partially full
    """ 

 
    df = pd.DataFrame()
    if not pick_list.empty:
#        pick_list = pick_list[pick_list['Excess'] == 1] # only when it is an excess unit can it be put in an empty location  
        df_pick_to = pd.DataFrame(pick_list.groupby(['WHID', 'Pick_To', 'Sprid','Sprid_Dims','MaxDim','MidDim','MinDim','Sprid_Cube','Excess'])['Pick_huid_units'].sum().reset_index())
    
        if not ppl_empty.empty:
            df = ppl_empty
             
            dict_pick_to = df_pick_to.set_index(['WHID','Pick_To']).to_dict('index')
        
            for j in ppl_empty.index:
                try:
                    key = [df['WHID'].iloc[j], df['Location_ID'].iloc[j]]
        
                    df['Sprid'].iloc[j] = dict_pick_to[tuple(key)]['Sprid']
                    df['Sprid_Dims'].iloc[j] = dict_pick_to[tuple(key)]['Sprid_Dims']        
                    df['MaxDim'].iloc[j] = dict_pick_to[tuple(key)]['MaxDim']        
                    df['MidDim'].iloc[j] = dict_pick_to[tuple(key)]['MidDim']        
                    df['MinDim'].iloc[j] = dict_pick_to[tuple(key)]['MinDim']       
                    df['Sprid_Cube'].iloc[j] = dict_pick_to[tuple(key)]['Sprid_Cube']           
                    df['OH_Units'].iloc[j] = dict_pick_to[tuple(key)]['Pick_huid_units']     
                except KeyError: 
                    pass # in case lookup key not in dict index
                
            df['f'] = np.vectorize(calc, otypes=["O"]) (df['Depth'], df['Width'], df['Height'], df['MaxDim'], df['MidDim'], df['MinDim'])   
            df['u'] = df['f'] - df['OH_Units'] 
            df['Utilization'] = df['OH_Units'] * df['Sprid_Cube'] / df['Liquid_Cube'] 
        else:
#            print('ppl_empty is empty')
            df = ppl_empty
            pass
        
    else:
#        print('pick list is empty')
        df = ppl_empty
        pass
    
    return df
  

def init_snapshot(opl, ppl):
    opl_init = opl   
    ppl_init = ppl
  
    client = bigquery.Client(project='ops-prod')
    # Define table name, in format dataset.table_name
    opl_init_table = 'supply_chain.tbl_opl_init_snapshot'
    ppl_init_table = 'supply_chain.tbl_ppl_init_snapshot'

    # Load data to BQ
    job_opl = client.load_table_from_dataframe(opl_init, opl_init_table)
    job_ppl = client.load_table_from_dataframe(ppl_init, ppl_init_table)
    
    print('Init OPL and PPL snapshots have been taken and uploaded into big query')
    return job_opl, job_ppl



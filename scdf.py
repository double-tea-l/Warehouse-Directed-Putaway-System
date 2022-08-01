# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 19:11:06 2020

@author: tl759k
"""

import pandas as pd
from collections import defaultdict


"""
    Script defines possible pick and put scenarios  
"""

def scenario2(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand) -> pd.DataFrame():
    
    """
    Scenario 2: at least 1 location in opl gives the exact num of units need to pick (u)
    :return: rank by util asc and pick the first exact full pallet
    """
    
    opl_sprid_cand = opl_sprid_cand[opl_sprid_cand['Sprid_Units'] == u]
    opl_sprid_cand = opl_sprid_cand.sort_values(by = ['Utilization','Location_ID'], ascending = True).reset_index(drop = True)
    
    j = 0 # pick j rows of sprid (the first one in this case)
    
    # pick from locations
    df = opl_sprid_cand[opl_sprid_cand.index == j]
    
    # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
    df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
    df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
    
    # pick to location
    df['Pick_To'] = ppl_pf['Location_ID'].iloc[i] 
   
    # no excess sprid and units under scenario 2
    df['Excess'] = 0    
    
    df['Rack_Dims'] = ppl_pf['Rack_Dims'].iloc[i] 
    df['Liquid_Cube'] =  ppl_pf['Liquid_Cube'].iloc[i] 
    
    return df


def scenario3(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand) -> pd.DataFrame():

    """
    Scenario 3: sum of all opl_cand units is less than units need to pick (u)
    :return: pick from all opl_cand locations
    """
    opl_sprid_cand = opl_sprid_cand.sort_values(by = ['Utilization','Location_ID'], ascending = True).reset_index(drop = True)
    
    # pick from all locations under scenario 3
    df = opl_sprid_cand
    
    # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
    df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
    df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
        
    # pick to location
    df['Pick_To'] = ppl_pf['Location_ID'].iloc[i]    
   
    # no excess sprid and units under scenario 3
    df['Excess'] = 0   
    
    df['Rack_Dims'] = ppl_pf['Rack_Dims'].iloc[i] 
    df['Liquid_Cube'] =  ppl_pf['Liquid_Cube'].iloc[i] 

    return df   
    
    
def scenario5(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand, ppl_empty) -> pd.DataFrame():

    """
    Scenario 5: sum of sprid units > u, min of sprid units < u and there's no combination gives u
    :return: pick in sequence and remain excess units to empty ppl locations, if empty ppl locations are not enough, then skip
    """ 

    # test logic:---------------------------------------------------------------
#    opl_huid_cand = pd.read_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\input\excess_units_logic\opl_huid_cand.csv').drop(['Unnamed: 0'],axis=1)
#    opl_huid_cand = opl_huid_cand[['WHID','Rack_Type','Location_ID','Sprid','hu_id','huid_units']]
#    ppl = pd.read_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\input\excess_units_logic\ppl_pf.csv').drop(['Unnamed: 0'],axis=1)
#    opl_sprid_cand = pd.read_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\input\excess_units_logic\opl_sprid_cand2.csv').drop(['Unnamed: 0'],axis=1)
#    u = 2
#    i = 0
    
#    ppl_pf = ppl[ppl['OH_Units'] != 0].reset_index(drop = True)
#    ppl_empty = ppl[ppl['OH_Units'] == 0].reset_index(drop = True)
    # comment after testing---------------------------------------------------

    opl_sprid_cand = opl_sprid_cand.sort_values(by = ['Utilization','Location_ID'], ascending = True).reset_index(drop = True)    
   
    # pick pick_sum units until index j
    pick_sum = 0  
    for j in opl_sprid_cand.index:
        p = opl_sprid_cand['Sprid_Units'].iloc[j]
        pick_sum = p + pick_sum
        
        if pick_sum < u:
            j = j + 1
        else:
            break
        
#    p_j = u # units to pick from index j
    r_j = pick_sum - u # units remain excess from index j
    
    
    # step 1 determine if ppf locations with same rack dims and same sprid dims are sufficient for excess units putaway
    same_ppf = ppl_pf[ppl_pf.index > i] # filter ppf locations that are not the current one
    same_ppf = same_ppf[same_ppf['Rack_Dims'] == ppl_pf['Rack_Dims'].iloc[i]] #filter ppf locations that have the same rack dims
    same_ppf = same_ppf[same_ppf['Sprid'] == ppl_pf['Sprid'].iloc[i]].reset_index(drop = True)
    ppf_avail = same_ppf['u'].sum()
    f = ppl_pf['f'].iloc[i]
    
    # determine if emtpy locations are sufficient for excess units putaway
    # 理想情况下，完全根据rack dim和sprid dim决定，是否fit,有多少空余。现在先简化为，filter和该PPL同样类型的Rack dim locs。empty loc的f = ppl_pf的f。   
    if not ppl_empty.empty:
        num_loc = ppl_empty[ppl_empty['Rack_Dims'] == ppl_pf['Rack_Dims'].iloc[i]]['Location_ID'].nunique()
        f = ppl_pf['f'].iloc[i]
        avail = num_loc * f
        ppl_empty = ppl_empty[ppl_empty['Rack_Dims'] == ppl_pf['Rack_Dims'].iloc[i]] 
    else:
        avail = 0
            
    df = pd.DataFrame()
    if ppf_avail< r_j: #if ppl_pf have fit all excess units, then put in ppl_pf locations
       
        if avail + ppf_avail < r_j: #if ppl_pf + ppl_empty can fit excess units, then put ppl_pf first, and the second excess goes to ppl_empty locations   
#            print('Skip because excess units dont have enough empty locations for putaway')
            pass
        
        elif ppf_avail == 0:
            
            df = opl_sprid_cand[opl_sprid_cand.index <= j] #pick until index j
            # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
            df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
            df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
            
            # pick to location and excess flag
            n = 0
            l = 0
            df['Pick_To'] = 0
            df['Excess'] = 0       
            for m in df.index:
                if m <= u-1:
                    df['Pick_To'].iloc[m] = ppl_pf['Location_ID'].iloc[i]
                    df['Excess'].iloc[m] = 0
                else:
                    
                    df['Pick_To'].iloc[m] = ppl_empty['Location_ID'].iloc[l]
                    n = n + 1
                    l = n // f # within f, should all be put in 1 location
                    df['Excess'].iloc[m] = 1
                    
        else:
            df = opl_sprid_cand[opl_sprid_cand.index <= j] #pick until index j
            # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
            df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
            df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
            
            # determine to which index can 1st excess units be put in same_ppl_pf location
            s_index = same_ppf.index.max()
            
            # pick to location and excess flag
            n = 0
            l = 0
            l2 = 0
            n2 = 0
            df['Pick_To'] = 0
            df['Excess'] = 0       
            for m in df.index:
                if m <= u-1:
                    df['Pick_To'].iloc[m] = ppl_pf['Location_ID'].iloc[i]
                    df['Excess'].iloc[m] = 0
                elif l <= s_index:
                    df['Pick_To'].iloc[m] = same_ppf['Location_ID'].iloc[l]                    
                    s_u = same_ppf['u'].iloc[l]  # num of space avail
                    n = n + 1
                    l = n // s_u # within s_u, should all be put in one location
                    df['Excess'].iloc[m] = 1  
                else:                    
                    df['Pick_To'].iloc[m] = ppl_empty['Location_ID'].iloc[l2]     
                    n2 = n2 + 1
                    l2 = n2 // f
                    df['Excess'].iloc[m] = 1  
    else:
        
        df = opl_sprid_cand[opl_sprid_cand.index <= j] #pick until index j
        # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
        df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
        df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
        
        # pick to location and excess flag
        n = 0
        l = 0
        df['Pick_To'] = 0
        df['Excess'] = 0       
        for m in df.index:
            if m <= u-1:
                df['Pick_To'].iloc[m] = ppl_pf['Location_ID'].iloc[i]
                df['Excess'].iloc[m] = 0
            else:
                
                df['Pick_To'].iloc[m] = same_ppf['Location_ID'].iloc[l]
                n = n + 1
                l = n // f # within f, should all be put in 1 location
                df['Excess'].iloc[m] = 1  
                
    df['Rack_Dims'] = ppl_pf['Rack_Dims'].iloc[i] 
    df['Liquid_Cube'] =  ppl_pf['Liquid_Cube'].iloc[i]         
        
    return df 
        
        
def scenario6(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand) -> pd.DataFrame():        
        
    """
    Scenario 6: sum of sprid units > u, there's at least one combination gives u
    :return: choose the comb that will free up max num of locations, 
             if same, then pick any combination (the first one) and remain excess units to empty ppl locations, 
             if empty ppl locations are not enough, then skip
    """        
        
    opl_sprid_cand = opl_sprid_cand.sort_values(by = ['Utilization','Location_ID'], ascending = True).reset_index(drop = True)            
        
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

    nums = opl_sprid_cand['Sprid_Units'].to_list()    
    l = len(nums)
    target = u


    result = subset_sum(nums, target, l, partial = [], index = [])     
    df_comb = pd.DataFrame(result, columns = ['partial', 'index'])
    df_comb['len'] = [len(i) for i in df_comb['partial'].values]

    # choose the comb that will free up max num of locations    
    df_comb = df_comb[df_comb['len'] == df_comb['len'].max()].reset_index(drop = True)    
      
    df = pd.DataFrame()
    if not df_comb.empty: 
        
        index = df_comb['index'][0] # pick the first index comb      

        for j in index:

            tmp_df = opl_sprid_cand[opl_sprid_cand.index == j]
#            print(j, tmp_df)          
            df = pd.concat([df, tmp_df]).reset_index(drop = True)
        
        # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
        df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
        df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
                           
        # pick to location
        df['Pick_To'] = ppl_pf['Location_ID'].iloc[i]    
           
        # no excess sprid and units under scenario 6
        df['Excess'] = 0   
        
    else:
        pass
    
    df['Rack_Dims'] = ppl_pf['Rack_Dims'].iloc[i] 
    df['Liquid_Cube'] =  ppl_pf['Liquid_Cube'].iloc[i] 
    
    return df



def scenario10(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand, ppl_empty) -> pd.DataFrame():        
        
    """
    Scenario 10: min of opl sprid units > u, any location will have excess units
    :return: pick in sequence rank by bin fill rate, units on hand, location id etc. and remain excess units, if empty ppl locations are not enough, then skip
    """  
    
    opl_sprid_cand = opl_sprid_cand.sort_values(by = ['Utilization','Location_ID'], ascending = True).reset_index(drop = True)            
    
    j = 0 # pick from the first location
    
    p_j = u # units to pick from index j
    r_j = opl_sprid_cand['Sprid_Units'].iloc[j] - p_j # units remain excess from index j
    
    # step 1 determine if ppf locations with same rack dims and same sprid dims are sufficient for excess units putaway
    same_ppf = ppl_pf[ppl_pf.index > i] # filter ppf locations that are not the current one
    same_ppf = same_ppf[same_ppf['Rack_Dims'] == ppl_pf['Rack_Dims'].iloc[i]] #filter ppf locations that have the same rack dims
    same_ppf = same_ppf[same_ppf['Sprid'] == ppl_pf['Sprid'].iloc[i]].reset_index(drop = True)
    ppf_avail = same_ppf['u'].sum()
    f = ppl_pf['f'].iloc[i]
    
    # determine if emtpy locations are sufficient for excess units putaway
    # 理想情况下，完全根据rack dim和sprid dim决定，是否fit,有多少空余。现在先简化为，filter和该PPL同样类型的Rack dim locs。empty loc的f = ppl_pf的f。
    if not ppl_empty.empty:
        num_loc = ppl_empty[ppl_empty['Rack_Dims'] == ppl_pf['Rack_Dims'].iloc[i]]['Location_ID'].nunique()
        f = ppl_pf['f'].iloc[i]
        avail = num_loc * f
        ppl_empty = ppl_empty[ppl_empty['Rack_Dims'] == ppl_pf['Rack_Dims'].iloc[i]]  
    else:
        avail = 0
    
    df = pd.DataFrame()  
    if ppf_avail < r_j:
        
        if  ppf_avail + avail < r_j:        
#            print('Skip because excess units dont have enough empty locations for putaway')
            pass
        
        elif ppf_avail == 0:
            
            df = opl_sprid_cand[opl_sprid_cand.index == j] #pick from index j
            # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
            df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
            df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
            
            # pick to location and excess flag
            n = 0
            l = 0
            df['Pick_To'] = 0
            df['Excess'] = 0       
            for m in df.index:
                if m <= u-1:
                    df['Pick_To'].iloc[m] = ppl_pf['Location_ID'].iloc[i]
                    df['Excess'].iloc[m] = 0
                else:
                    
                    df['Pick_To'].iloc[m] = ppl_empty['Location_ID'].iloc[l]
                    n = n + 1
                    l = n // f # within f, should all be put in 1 location
                    df['Excess'].iloc[m] = 1    
                    
        else:
            df = opl_sprid_cand[opl_sprid_cand.index <= j] #pick until index j
            # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
            df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
            df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
            
            # determine to which index can 1st excess units be put in same_ppl_pf location
            s_index = same_ppf.index.max()
            
            # pick to location and excess flag
            n = 0
            l = 0
            l2 = 0
            n2 = 0
            df['Pick_To'] = 0
            df['Excess'] = 0       
            for m in df.index:
                if m <= u-1:
                    df['Pick_To'].iloc[m] = ppl_pf['Location_ID'].iloc[i]
                    df['Excess'].iloc[m] = 0
                elif l <= s_index:
                    df['Pick_To'].iloc[m] = same_ppf['Location_ID'].iloc[l]                    
                    s_u = same_ppf['u'].iloc[l]  # num of space avail
                    n = n + 1
                    l = n // s_u # within s_u, should all be put in one location
                    df['Excess'].iloc[m] = 1  
                else:                    
                    df['Pick_To'].iloc[m] = ppl_empty['Location_ID'].iloc[l2]     
                    n2 = n2 + 1
                    l2 = n2 // f
                    df['Excess'].iloc[m] = 1  
                  
    else:
        df = opl_sprid_cand[opl_sprid_cand.index == j] #pick from index j
        # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
        df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
        df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
        
        # pick to location and excess flag
        n = 0
        l = 0
        df['Pick_To'] = 0
        df['Excess'] = 0       
        for m in df.index:
            if m <= u-1:
                df['Pick_To'].iloc[m] = ppl_pf['Location_ID'].iloc[i]
                df['Excess'].iloc[m] = 0
            else:
                
                df['Pick_To'].iloc[m] = same_ppf['Location_ID'].iloc[l]
                n = n + 1
                l = n // f # within f, should all be put in 1 location
                df['Excess'].iloc[m] = 1 
        
    df['Rack_Dims'] = ppl_pf['Rack_Dims'].iloc[i] 
    df['Liquid_Cube'] =  ppl_pf['Liquid_Cube'].iloc[i] 
          
    return df 



def scenario10_empty(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand) -> pd.DataFrame():        
        
    """
    Scenario 10: min of opl sprid units > u, any location will have excess units
    :return: pick in sequence rank by bin fill rate, units on hand, location id etc. and remain excess units, if empty ppl locations are not enough, then skip
    """  
    
    opl_sprid_cand = opl_sprid_cand.sort_values(by = ['Utilization','Location_ID'], ascending = True).reset_index(drop = True)            
    
    j = 0 # pick from the first location
    
    p_j = u # units to pick from index j
    r_j = opl_sprid_cand['Sprid_Units'].iloc[j] - p_j # units remain excess from index j
    
    # determine if emtpy locations are sufficient for excess units putaway
    # 理想情况下，完全根据rack dim和sprid dim决定，是否fit,有多少空余。现在先简化为，filter和该PPL同样类型的Rack dim locs。empty loc的f = ppl_pf的f。
    # for empty location logic, ppl_pf = ppl_empty, ppl_empty is empty
    ppl_empty = ppl_pf[ppl_pf['OH_Units'] == 0].reset_index(drop = True)  
    ppl_empty = ppl_pf[ppl_pf.index > i].reset_index(drop = True)   # can't be the current location we're trying to fill

    
    if not ppl_empty.empty:

        num_loc = ppl_empty[ppl_empty['Rack_Dims'] == ppl_pf['Rack_Dims'].iloc[i]]['Location_ID'].nunique()
        f = ppl_pf['f'].iloc[i]
        avail = num_loc * f
    else:
        avail = 0
        
    df = pd.DataFrame()
    if r_j > avail:
        
#        print('Skip because excess units dont have enough empty locations for putaway')
        pass
    
    else:
        
        df = opl_sprid_cand[opl_sprid_cand.index == j] #pick from index j
        # attach hu_id and huid units (all hu_id units for the sprid under scenario 2)
        df = pd.merge(df, opl_huid_cand, on = ['WHID','Rack_Type','Location_ID','Sprid'], how = 'left') # put left join for now, can check outer join for debug later on
        df.rename(columns = {'Location_ID':'Pick_From', 'Sprid_Units': 'Pick_Sprid_Units', 'huid_units': 'Pick_huid_units'}, inplace = True)
        
        # pick to location and excess flag
        n = 0
        l = 0
        df['Pick_To'] = 0
        df['Excess'] = 0       
        for m in df.index:
            if m <= u-1:
                df['Pick_To'].iloc[m] = ppl_pf['Location_ID'].iloc[i]
                df['Excess'].iloc[m] = 0
            else:
                
                df['Pick_To'].iloc[m] = ppl_empty['Location_ID'].iloc[l]
                n = n + 1
                l = n // f # within f, should all be put in 1 location
                df['Excess'].iloc[m] = 1     

    df['Rack_Dims'] = ppl_pf['Rack_Dims'].iloc[i] 
    df['Liquid_Cube'] =  ppl_pf['Liquid_Cube'].iloc[i] 
                
    return df 

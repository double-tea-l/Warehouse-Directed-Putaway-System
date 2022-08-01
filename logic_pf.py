# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 19:31:32 2020

@author: tl759k
"""

# import libraries
import pandas as pd
import numpy as np
import utils # other fucntions definition
import scdf # scenarios definition
import prep #gbq
#import prep2 #sql
"""
    Main code Part 1: Partially Full Prime Pick Location Picking and Putaway Logic
"""

# import opl and ppl init
## from gbq
opl = prep.opl
ppl = prep.ppl

### from sql
#opl = prep2.opl
#ppl = prep2.ppl

# from csv of saved sql
#opl = pd.read_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\snapshots\init\opl_init.csv', index_col = False).drop(['Unnamed: 0'],axis=1)
#opl = pd.read_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\snapshots\init\opl_init.csv', index_col = False)
#ppl = pd.read_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\snapshots\init\ppl_init.csv', index_col = False).drop(['Unnamed: 0'],axis=1)

#opl.columns
# define model variables-------------------------------------------------------
r1 = 0.85 # bin fill rate threshold for ppl
#r2 = 0.50 # consolidation util threshold for opl
inc = 0.5
f = 8

# best fit sprid candidate list of ppl-----------------------------------------
rack_dims = list(np.unique(ppl['Rack_Dims'].values))
df_sprid = utils.best_sprid_cand(rack_dims, r1, inc, f)

# 4.1 best sprid candidates for unique ppl rack dims; one sprid can only have one best fit rack type
df_sprid = df_sprid[['Rack_Dims','Sprid_Dims','f','Util','Rank','Util/f']]
df_sprid = df_sprid.sort_values(by = ['Sprid_Dims', 'Util'], ascending = False).reset_index(drop = True)
df_sprid['C'] = df_sprid.groupby(['Sprid_Dims']).cumcount()+1
df_sprid = df_sprid[df_sprid['C'] == 1].reset_index(drop = True)

#df_sprid.to_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\snapshots\init\df_sprid_init.csv')
# filter opl locations based on the best sprid list
# this is required for pilot run given we need to determine which location to pick from
df_opl = opl[opl['Sprid_Dims'].isin(df_sprid['Sprid_Dims'])].reset_index(drop = True)

#------------------------------------------------------------------------------
# Step 1 Determine f and u for ppl---------------------------------------------
# calc max units per loc (f) and units required to fill (u) for each prime pick location (ppl)
ppl['f'] = np.vectorize(utils.calc, otypes=["O"]) (ppl['Depth'], ppl['Width'], ppl['Height'], ppl['MaxDim'], ppl['MidDim'], ppl['MinDim'])   
ppl['u'] = np.maximum(ppl['f'] - ppl['OH_Units'], 0)


# take snapshots to upload intit opl and ppl list into big query for archive
utils.init_snapshot(df_opl, ppl) # turn off for test runs

# Step 2 Prepare data----------------------------------------------------------
# ppl: Seperate ppl_pf and ppl_empty: split ppl into two dataframes: partially full locations (ppl_pf) and empty locations (ppl_empty)
ppl_pf = ppl[ppl['OH_Units'] != 0].reset_index(drop = True)
ppl_empty = ppl[ppl['OH_Units'] == 0].reset_index(drop = True)

# drop ppf_pf where u = 0
ppl_pf = ppl_pf[ppl_pf['u'] != 0].reset_index(drop = True)

# drop ppf_pf where on hand sprid dim is not a best fit sprid dim
ppl_pf = ppl_pf[ppl_pf['Sprid_Dims'].isin(df_sprid['Sprid_Dims'].unique())].reset_index(drop = True)

# opl: Seperate opl sprid and opl huid
opl_sprid = df_opl[['WHID','Rack_Type', 'Location_ID','Liquid_Cube','Utilization'
                 ,'Sprid','Sprid_Cube','Sprid_Units','MaxDim','MidDim','MinDim','Sprid_Dims']].drop_duplicates().reset_index(drop = True)

#opl_sprid = opl_sprid[['Sprid','Sprid_Units', 'WHID','Rack_Type','Location_ID','Liquid_Cube','Utilization'
#                 ,'Sprid_Cube','MaxDim','MidDim','MinDim','Sprid_Dims']] # for coding visibility purpose, need to comment after code is complete.

opl_huid = df_opl[['WHID','Rack_Type','Location_ID','Sprid','hu_id','huid_units']]


# Step 3 Loop for ppl_pf-------------------------------------------------------
# sort ppl_pf by utilization desc: try to fill fullest locations first
ppl_pf = ppl_pf.sort_values(by = ['Utilization', 'OH_Units'], ascending = False).reset_index(drop = True)
#ppl_pf.to_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\input\excess_units_logic\ppl_pf.csv')
#opl_sprid.to_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\input\excess_units_logic\opl_sprid_cand.csv')

# start to loop
output = pd.DataFrame()
if not ppl_pf.empty:    
    
    for i in ppl_pf.index:
    #    i= 2
        if not opl_sprid.empty:
    #        i = 1
            u = ppl_pf['u'].iloc[i]
            sprid = ppl_pf['Sprid'].iloc[i]
            
            # filter opl candidates by lookup sprid
            opl_sprid_cand = opl_sprid[opl_sprid['Sprid'] == sprid].reset_index(drop = True)
            opl_huid_cand = opl_huid[opl_huid['Sprid'] == sprid].reset_index(drop = True)
            
            pick_list = pd.DataFrame()
            
            # scenario 1 complete; skip
            if ppl_pf['u'].iloc[i] == 0:
                
                """
                Scenario 1: u = 0, no need to pick and put
                :return: skip this ppl location
                """
                print(i, 'Scenario 1')
                
                pass
            
            # scenario 2 complete; no excess units        
            elif u in opl_sprid_cand['Sprid_Units'].values:
                
                """
                Scenario 2: at least 1 location in opl gives the exact num of units need to pick (u)
                :return: rank by util asc and pick the first exact full pallet
                """
                print(i, 'Scenario 2')
                
                pick_list = scdf.scenario2(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand)
                opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid)
                opl_huid = utils.recalc_opl_huid(pick_list, opl_huid)
                ppl_pf = utils.recalc_ppl_pf(pick_list, ppl_pf)
                
            # scenario 3 complete; no excess units             
            elif opl_sprid_cand['Sprid_Units'].sum() <= u:
                
                """
                Scenario 3: sum of all opl_cand units is less than units need to pick (u)
                :return: pick from all opl_cand locations
                """
                print(i, 'Scenario 3')
                
                pick_list = scdf.scenario3(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand)
                opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid)
                opl_huid = utils.recalc_opl_huid(pick_list, opl_huid)
                ppl_pf = utils.recalc_ppl_pf(pick_list, ppl_pf)    
                
            # scenario 5 complete; excess units
            elif opl_sprid_cand['Sprid_Units'].sum() > u and opl_sprid_cand['Sprid_Units'].min() < u and utils.comb(opl_sprid_cand, u) == 0 :
                
                """
                Scenario 5: sum of sprid units > u, min of sprid units < u and there's no combination gives u
                :return: pick in sequence and remain excess units to empty ppl locations, if empty ppl locations are not enough, then skip
                """
                print(i, 'Scenario 5')
                
                pick_list = scdf.scenario5(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand, ppl_empty) 
                opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid)
                opl_huid = utils.recalc_opl_huid(pick_list, opl_huid)
                ppl_pf = utils.recalc_ppl_pf(pick_list, ppl_pf)                
                ppl_empty = utils.recalc_ppl_empty(pick_list, ppl_empty)
                
    
            # scenario 6 complete; no excess units
            elif opl_sprid_cand['Sprid_Units'].sum() > u and utils.comb(opl_sprid_cand, u) == 1:
    
                """
                Scenario 6: sum of sprid units > u, there's at least one combination gives u
                :return: pick any combination (the first one) and remain excess units to empty ppl locations, if empty ppl locations are not enough, then skip
                """
                print(i, 'Scenario 6')
    
                pick_list = scdf.scenario6(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand) 
                opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid)
                opl_huid = utils.recalc_opl_huid(pick_list, opl_huid)
                ppl_pf = utils.recalc_ppl_pf(pick_list, ppl_pf)                
    
    
            # scenario 10; excess units
            elif opl_sprid_cand['Sprid_Units'].min() > u:
                
                """
                Scenario 10: min of opl sprid units > u, any location will have excess units
                :return: pick in sequence rank by bin fill rate, units on hand, location id etc. and remain excess units, if empty ppl locations are not enough, then skip
                """
                print(i, 'Scenario 10')
        
                pick_list = scdf.scenario10(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand, ppl_empty) 
                opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid)
                opl_huid = utils.recalc_opl_huid(pick_list, opl_huid)
                ppl_pf = utils.recalc_ppl_pf(pick_list, ppl_pf)                
                ppl_empty = utils.recalc_ppl_empty(pick_list, ppl_empty)
    
        
            # renew ppl_pf and ppl_empty after each iteration   
            # append new pf locations to ppl_pf   
            tmp_pf = ppl_empty[ppl_empty['OH_Units'] > 0]
            ppl_pf = pd.concat([ppl_pf, tmp_pf]).reset_index(drop = True)  
            # drop new pf locations from ppl_empty
            ppl_empty = ppl_empty[ppl_empty['OH_Units'] == 0].reset_index(drop = True)
                    
            opl_sprid = opl_sprid[opl_sprid['Sprid_Units'] != 0].reset_index(drop = True) # delete opl sprid locations that have been emptied
            opl_huid = opl_huid[opl_huid['huid_units'] != 0].reset_index(drop = True) # delete opl huid locations that have been emptied
    #        print(ppl_pf, opl_sprid)
            # append pick_list
            output = pd.concat([output, pick_list])    
    
    
        else:
            print('Skip because nothing to pick from opl locations')
            pass    
else:
    print('PPL is empty')
    pass    
# end of step 3----------------------------------------------------------------
      
df_output = output
df_ppl_pf = ppl_pf 
df_ppl_empty = ppl_empty
df_opl_sprid = opl_sprid
df_opl_huid = opl_huid

#df_output.to_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\snapshots\pick_list\pf_logic.csv')
# end of partially full location logic ----------------------------------------
#------------------------------------------------------------------------------

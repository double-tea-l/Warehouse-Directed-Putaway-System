# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 00:20:22 2020

@author: tl759k
"""
import schedule
import time


"""
    Main code Part 2: Empty Prime Pick Location Picking and Putaway Logic
"""

def run_model():
    
    # import libraries
    import pandas as pd
    import numpy as np
    import utils # other fucntions definition
    import scdf # scenarios definition
    #from sqlalchemy import create_engine
    import logic_pf
    from google.cloud import bigquery
    import datetime

          
    # define model variables-------------------------------------------------------
    r1 = 0.85 # bin fill rate threshold for ppl
    inc = 0.5
    f = 8
    
    # remaining empty location
    ppl_empty = logic_pf.df_ppl_empty
    opl_sprid_cand = logic_pf.df_opl_sprid
    opl_huid_cand = logic_pf.df_opl_huid

    # 4.0 best fit sprid candidate list of ppl-----------------------------------------
    rack_dims = list(np.unique(ppl_empty['Rack_Dims'].values))
    df_sprid = utils.best_sprid_cand(rack_dims, r1, inc, f)
    
    # 4.1 best sprid candidates for empty locations rack dims
    df_sprid = df_sprid[['Rack_Dims','Sprid_Dims','f','Util','Rank','Util/f']]
    df_sprid = df_sprid.sort_values(by = ['Sprid_Dims', 'Util'], ascending = False).reset_index(drop = True)
    df_sprid['C'] = df_sprid.groupby(['Sprid_Dims']).cumcount()+1
    df_sprid = df_sprid[df_sprid['C'] == 1].reset_index(drop = True)  
    
    # 4.2 check if those sprid candidates are available on hand in opl locations
    df_opl_sprid = pd.merge(opl_sprid_cand, df_sprid, on = ['Sprid_Dims'], how = 'inner')
    
    # 4.3 rank by max potential oh util based on existing on hand units (or by 'Rank')
    df_opl_sprid['max_oh_util'] = df_opl_sprid['Util/f'] * np.minimum(df_opl_sprid['Sprid_Units'], df_opl_sprid['f'])
    df_opl_sprid = df_opl_sprid.sort_values(by = ['Rack_Dims', 'max_oh_util'], ascending = False).reset_index(drop = True)
#    df_opl_sprid = df_opl_sprid[df_opl_sprid['max_oh_util'] >= 0.85] # if only has 1 or 2 units, no point to consolidate.
    df_opl_sprid = df_opl_sprid.sort_values(by = ['max_oh_util'], ascending = False).reset_index(drop = True)
    df_opl_huid = opl_huid_cand[opl_huid_cand['Sprid'].isin(opl_huid_cand['Sprid'])]
    
    # make empty as ppf_pf and assumes there's no empty location, so that the functions can carry on
    ppl_pf_raw = ppl_empty
    ppl_empty = ppl_empty.drop(ppl_empty.index)
    
    df_cand_opl_sprid_raw = df_opl_sprid[['Sprid','Sprid_Dims','MaxDim','MidDim','MinDim','Sprid_Cube', 'Rack_Dims']].drop_duplicates()
    df_cand_opl_sprid_raw = df_cand_opl_sprid_raw.reset_index(drop = True)

    ppl_pf_final = pd.DataFrame()
    ppl_empty_final = pd.DataFrame()

    done_ppf_pf = pd.DataFrame()
    df_output = pd.DataFrame()
    
    
    for rack_dim in rack_dims:
#        rack_dim = '42x50x20'
        df_cand_opl_sprid = df_cand_opl_sprid_raw[df_cand_opl_sprid_raw['Rack_Dims'] == rack_dim]
        ppl_pf = ppl_pf_raw[ppl_pf_raw['Rack_Dims'] == rack_dim].reset_index(drop = True)
        
        sprid_list = df_cand_opl_sprid['Sprid'].unique()
        
        print(rack_dim, ppl_pf)
    
        for sprid in sprid_list:
#            sprid = 'KD2260.14386703'
            
            d = df_cand_opl_sprid.set_index(['Sprid']).to_dict('index')
            key = sprid

            ppl_pf['Sprid'] = sprid
            ppl_pf['Sprid_Dims'] = d[key]['Sprid_Dims']        
            ppl_pf['MaxDim'] = d[key]['MaxDim']        
            ppl_pf['MidDim'] = d[key]['MidDim']        
            ppl_pf['MinDim'] = d[key]['MinDim']       
            ppl_pf['Sprid_Cube'] = d[key]['Sprid_Cube']           
                
            ppl_pf['f'] = np.vectorize(utils.calc, otypes=["O"]) (ppl_pf['Depth'], ppl_pf['Width'], ppl_pf['Height'], ppl_pf['MaxDim'], ppl_pf['MidDim'], ppl_pf['MinDim'])   
            ppl_pf['u'] = ppl_pf['f'] - ppl_pf['OH_Units'] 
    
            # filter opl candidates by lookup sprid
            opl_sprid_cand = df_opl_sprid[df_opl_sprid['Sprid'] == sprid].reset_index(drop = True)
            opl_huid_cand = df_opl_huid[df_opl_huid['Sprid'] == sprid].reset_index(drop = True)
        
            output = pd.DataFrame()
            
            for i in ppl_pf.index:
              
                location_id = ppl_pf['Location_ID'].iloc[i]
           
                if not opl_sprid_cand.empty:
        
                    u = ppl_pf['u'].iloc[i]
                    sprid = ppl_pf['Sprid'].iloc[i]
                          
                    pick_list = pd.DataFrame()
                    
                    # scenario 1 complete; skip
                    if ppl_pf['u'].iloc[i] == 0:
                        
                        """
                        Scenario 1: u = 0, no need to pick and put
                        :return: skip this ppl location
                        """
                        print(sprid, i, location_id, 'Scenario 1')
                        
                        opl_sprid_cand = opl_sprid_cand
                        opl_huid_cand = opl_huid_cand
                        
                    
                    # scenario 2 complete; no excess units        
                    elif u in opl_sprid_cand['Sprid_Units'].values:
                        
                        """
                        Scenario 2: at least 1 location in opl gives the exact num of units need to pick (u)
                        :return: rank by util asc and pick the first exact full pallet
                        """
                        print(sprid, i, location_id, 'Scenario 2')
                        
                        pick_list = scdf.scenario2(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand)
                        opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid_cand)
                        opl_huid = utils.recalc_opl_huid(pick_list, opl_huid_cand)
                        ppl_pf = utils.recalc_ppl_empty(pick_list, ppl_pf)
                        
                        opl_sprid_cand = opl_sprid[opl_sprid['Sprid_Units'] != 0].reset_index(drop = True) # delete opl sprid locations that have been emptied
                        opl_huid_cand = opl_huid[opl_huid['huid_units'] != 0].reset_index(drop = True) # delete opl huid locations that have been emptied
        
                        
                    # scenario 3 complete; no excess units             
                    elif opl_sprid_cand['Sprid_Units'].sum() <= u:
                        
                        """
                        Scenario 3: sum of all opl_cand units is less than units need to pick (u)
                        :return: pick from all opl_cand locations
                        """
                        print(sprid, i, location_id, 'Scenario 3')
                        
                        pick_list = scdf.scenario3(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand)
                        opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid_cand)
                        opl_huid = utils.recalc_opl_huid(pick_list, opl_huid_cand)
                        ppl_pf = utils.recalc_ppl_empty(pick_list, ppl_pf)    
        
                        opl_sprid_cand = opl_sprid[opl_sprid['Sprid_Units'] != 0].reset_index(drop = True) # delete opl sprid locations that have been emptied
                        opl_huid_cand = opl_huid[opl_huid['huid_units'] != 0].reset_index(drop = True) # delete opl huid locations that have been emptied
                        
                    # scenario 5 complete; excess units
                    elif opl_sprid_cand['Sprid_Units'].sum() > u and opl_sprid_cand['Sprid_Units'].min() < u and utils.comb(opl_sprid_cand, u) == 0 :
                        
                        """
                        Scenario 5: sum of sprid units > u, min of sprid units < u and there's no combination gives u
                        :return: pick in sequence and remain excess units to empty ppl locations, if empty ppl locations are not enough, then skip
                        """
                        print(sprid, i, location_id, 'Scenario 5')
                        
                        pick_list = scdf.scenario5(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand, ppl_empty) 
                        opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid_cand)
                        opl_huid = utils.recalc_opl_huid(pick_list, opl_huid_cand)
                        ppl_pf = utils.recalc_ppl_empty(pick_list, ppl_pf)                
                        ppl_empty = utils.recalc_ppl_empty(pick_list, ppl_empty)
                        
                        opl_sprid_cand = opl_sprid[opl_sprid['Sprid_Units'] != 0].reset_index(drop = True) # delete opl sprid locations that have been emptied
                        opl_huid_cand = opl_huid[opl_huid['huid_units'] != 0].reset_index(drop = True) # delete opl huid locations that have been emptied
        
            
                    # scenario 6 complete; no excess units
                    elif opl_sprid_cand['Sprid_Units'].sum() > u and utils.comb(opl_sprid_cand, u) == 1:
            
                        """
                        Scenario 6: sum of sprid units > u, there's at least one combination gives u
                        :return: pick any combination (the first one) and remain excess units to empty ppl locations, if empty ppl locations are not enough, then skip
                        """
                        print(sprid, i, location_id, 'Scenario 6')
            
                        pick_list = scdf.scenario6(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand) 
                        opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid_cand)
                        opl_huid = utils.recalc_opl_huid(pick_list, opl_huid_cand)
                        ppl_pf = utils.recalc_ppl_pf(pick_list, ppl_pf)                
            
                        opl_sprid_cand = opl_sprid[opl_sprid['Sprid_Units'] != 0].reset_index(drop = True) # delete opl sprid locations that have been emptied
                        opl_huid_cand = opl_huid[opl_huid['huid_units'] != 0].reset_index(drop = True) # delete opl huid locations that have been emptied
           
                    # scenario 10
                    elif opl_sprid_cand['Sprid_Units'].min() > u:
                        
                        """
                        Scenario 10: min of opl sprid units > u, any location will have excess units
                        :return: pick in sequence rank by bin fill rate, units on hand, location id etc. and remain excess units, if empty ppl locations are not enough, then skip
                        """
                        print(sprid, i, location_id, 'Scenario 10')
                
                        pick_list = scdf.scenario10_empty(i, u, ppl_pf, opl_sprid_cand, opl_huid_cand)
                        opl_sprid = utils.recalc_opl_sprid(pick_list, opl_sprid_cand)
                        opl_huid = utils.recalc_opl_huid(pick_list, opl_huid_cand)
                        ppl_pf = utils.recalc_ppl_empty(pick_list, ppl_pf)                
                        ppl_empty = utils.recalc_ppl_empty(pick_list, ppl_empty)
        
                        opl_sprid_cand = opl_sprid[opl_sprid['Sprid_Units'] != 0].reset_index(drop = True) # delete opl sprid locations that have been emptied
                        opl_huid_cand = opl_huid[opl_huid['huid_units'] != 0].reset_index(drop = True) # delete opl huid locations that have been emptied
        
        
                    tmp_pf = ppl_empty[ppl_empty['OH_Units'] > 0]
                    ppl_pf = pd.concat([ppl_pf, tmp_pf]).reset_index(drop = True)  
        
        
                    output = pd.concat([output, pick_list])   
                    
            
                else:
                    print(sprid, i,'Skip because nothing to pick from opl locations')
                    pass    
            
            df_output = pd.concat([df_output, output])    
            tmp_ppf_pf = ppl_pf[ppl_pf['OH_Units'] > 0]
            done_ppf_pf = pd.concat([done_ppf_pf, tmp_ppf_pf]).reset_index(drop = True)
            ppl_pf =  ppl_pf[ppl_pf['OH_Units'] == 0].reset_index(drop = True)
                
            
        ppl_pf_final = pd.concat([ppl_pf_final, done_ppf_pf]).reset_index(drop = True)
        ppl_pf_final['Run_time'] = datetime.datetime.now()     
        ppl_empty_final = pd.concat([ppl_empty_final, ppl_empty]).reset_index(drop = True)
        ppl_empty_final['Run_time'] = datetime.datetime.now() 
      
   
    final_pick_list = pd.DataFrame()
    output1 = logic_pf.df_output   
    output2 = df_output[[ 'Excess', 'Liquid_Cube', 'MaxDim', 'MidDim', 'MinDim', 'Pick_From',
       'Pick_Sprid_Units', 'Pick_To', 'Pick_huid_units', 'Rack_Dims',
       'Rack_Type', 'Sprid', 'Sprid_Cube', 'Sprid_Dims', 'Utilization', 'WHID',
       'hu_id']]
    
    final_pick_list = pd.concat([output1, output2]).reset_index(drop = True)
    
#    final_pick_list['Sprid_Cube'] = final_pick_list['MaxDim'] * final_pick_list['MidDim'] * final_pick_list['MinDim'] / 1728
    final_pick_list['Run_time'] = datetime.datetime.now() 
    
    # put results in google big query
    client = bigquery.Client(project='wf-gcp-us-ae-ops-prod')
    table = 'supply_chain.tbl_final_pick_list'
    job = client.load_table_from_dataframe(final_pick_list, table)
    completion_time = datetime.datetime.now() 
    
    print("%s%s" % ('The final pick list is complete and uploaded to GBQ at: \n', completion_time))
    
    return job

#run_model()

from apscheduler.schedulers.blocking import BlockingScheduler
sched = BlockingScheduler()
sched.add_job(run_model, 'cron', minute = 15)
sched.start()

#Setting the schedule for 5 am on Mondays
#schedule.every().hour.do(run_model)
#while True:
#    schedule.run_pending()
#    time.sleep(1)
#    
#from apscheduler.schedulers.blocking import BlockingScheduler
#scheduler = BlockingScheduler()
#scheduler.add_job(run_model, 'interval', minutes = 40)
#scheduler.start()

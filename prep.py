# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 10:35:30 2020

@author: tl759k
"""

import os
from pathlib import Path
from google.cloud import bigquery
import pandas as pd
import pyarrow.parquet as pq
#import utils


"""
    Prepare data inputs: OPL and PPL list
"""


# pull OPL and PPL snapshots from GBQ
def get_project_root() -> Path:
    """
    Gets Project root folder
    :return: project root folder
    """
    return Path(__file__).parent.parent


def pull_sql_query(
    query: str, project_id: str = "wf-gcp-us-ae-ops-prod"
) -> pd.DataFrame:
    """
   Queries google big query and returns query results as a pandas dataframe. Accepts either a query string or file name as an input.
    :param query: either a query string or file name
    :param project_id: GCP project user or server belongs to
    :return: Pandas dataframe of query results
    """
    root, ext = os.path.splitext(query)

    # Load query file as text
    if ext == ".sql":
        # Query Location
        query_loc = get_project_root() / "code" / query
        with open(query_loc, "r") as q:
            query = q.read()

    # Authenticate Query with local settings
    client = bigquery.Client(project=project_id)

    # Return Query Results as data frame
    return client.query(query).result().to_dataframe()



def load_opl_onhand_snapshot() -> pd.DataFrame:
    """
    Pulls opl on hand snapshot
    :return: cube per unit data frame
    """
    # query location
    query_loc_cpu = (
        get_project_root() / "code" / "opl_on_hand_snapshot_gbq.sql"
    )

    # pull data
    data = pull_sql_query(query=str(query_loc_cpu))

    return data


def load_ppl_onhand_snapshot() -> pd.DataFrame:
    """
    Pulls opl on hand snapshot
    :return: cube per unit data frame
    """
    # query location
    query_loc_cpu = (
        get_project_root() / "code" / "ppl_on_hand_snapshot_gbq.sql"
    )

    # pull data
    data = pull_sql_query(query=str(query_loc_cpu))

    return data


opl = load_opl_onhand_snapshot()
df_ppl = load_ppl_onhand_snapshot()

opl['WHID'] = opl['WHID'].astype(int)
opl.drop(columns = ['unit_weight'], inplace = True)


df_ppl['WHID'] = df_ppl['WHID'].astype(int)

#ppl = ppl[['Timestamp', 'WHID', 'Location_ID', 'Rack_Dims', 'Depth', 'Width',
#       'Height', 'Liquid_Cube', 'Sprid', 'Sprid_Dims', 'MaxDim', 'MidDim',
#       'MinDim', 'Sprid_Cube', 'Sprid_Units', 'Utilization']]

df_ppl.rename(columns = {'Sprid_Units': 'OH_Units'}, inplace = True)
ppl = df_ppl





ppl.rename(columns = {'Sprid_Units':'OH_Units'}, inplace = True)


# exclude incorrect dims sprid
exclusion = ['TKCL3472.17389714', 'KD2260.14386703'
             ,'FV48676.7480854','TINS1153.44942805','WLK1921.32224395','UBGK1068.36142649','HAZE1712.12770886'
             ,'SBFT1516.14599340','NTC1160.4468403','KUI5489.8099627']
opl = opl[~opl['Sprid'].isin(exclusion)].reset_index(drop = True)
opl['Sprid_Dims'] = opl['MaxDim'].astype(str) + 'x' + opl['MidDim'].astype(str) + 'x' + opl['MinDim'].astype(str)

# drop ppl location which has multiple sprid on hand
exclude_location = ppl[ppl['num_of_loc_id'] != 1]['Location_ID'].unique()
ppl = ppl[~ppl['Location_ID'].isin(exclude_location)].reset_index(drop = True)
ppl.drop(columns = ['num_of_loc_id'], inplace = True)



opl.to_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\snapshots\init\opl.csv')

ppl.to_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\snapshots\init\ppl.csv')






# take snapshots
#utils.init_snapshot(opl, ppl)


# pick top 10 to test
#ppl = ppl[ppl.index <= 20]
#opl = opl[opl['Sprid'] == 'ANEW1597.39625172'].reset_index(drop = True)

#ppl_1 = df_ppl[df_ppl['Rack_Dims'] == '42x21x20'].head(20)
#ppl_2 = df_ppl[df_ppl['Rack_Dims'] == '42x38x20'].head(20)
#ppl_3 = df_ppl[df_ppl['Rack_Dims'] == '42x50x20'].head(20)

#ppl = pd.concat([ppl_1, ppl_2, ppl_3]).reset_index(drop = True)

# debug
#opl = opl[opl['Sprid'] == 'KD2260.14386703'].reset_index(drop= True)
#opl.to_csv(r'C:\Users\tl759k\SQL\Sprid_Profile\consolidation_tool\output\opl_real.csv')
#ppl.rename(columns = {'Liquid_Cube' : 'Usable_Cube', 'Sprid_Units': 'OH_Units'}, inplace = True)
#opl.columns

## define variables to get best sprid candidates-------------------------------
#r1 = 0.85 # ppl
## rack dims
#rack_dims = ['42x21x20', '42x49x20']
#inc = 1
#f = 8
#
#df_sprid = utils.best_sprid_cand(rack_dims, r1, inc, f)
##-----------------------------------------------------------------------------

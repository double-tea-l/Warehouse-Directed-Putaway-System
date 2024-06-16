# Directed Putaway System for Piloting

This instruction outlies key assumptions, code logic and outputs of the consolidation tool. The purpose is to help developer track program details and relevant information. This is not a documentation for business user.

## 1. Objective
The objective of the consolidation project is to maximize bin fill rate of prime pick locations and free up as many under-utilized other pick locations as possible. Target is to reach a minimum of 85% bin fill rate at the prime pick locations with a stretch goal of >=95% bin fill rate. Additionally, the target location occupation rate is >=80% and stretch goal is >=95%.

## 2. Concept Definition
### 2.1 OPL (Other Pick Locations) ###
  - Rack types are PALLET, PALLET XL LONG and PALLET XL FLOOR
  - Zone != 'R' to exclude Cranbury 2
  - Under-utilized is defined as actual fill rate <= 0.5

### 2.2 PPL (Prime Pick Locations) ###
  - Rack type is HRD, Zone B and Asile 54
  - Rack usable dimensions are: 
     - 42x21x20: Bay <= 45 are racks with usable width as 21 inches
     - 42x38x20: Bay > 45 and even position number are racks with usable width as 38 inches
     - 42x50x20: Bay > 45 and odd position number are racks with usable width as 50 inches
     [Comment: Rack Dimensions according to the CAD design is slightly different. For the 21" wide locations, 1 side is on 44 1/8" wide, the other side is 45 3/8". We may eventually want to fine tune the usable cube accordingly, if possible after speaking with the Cranbury site after understanding their finger space requirements. The 50" location is actually 49 7/8" wide. So, if we have to leave some finger space, then the usable width would be 48". We should again talk to the site to understand this better. The conduits are a few inches inside from the franot face. That will allow the associate to pull the box from the front side which have 3.5" space on both sides.]
     
### 2.3 Best fit sprid candidate ###
  - Bin fill rate target is 85% while caculation threshold is 90%
     - given that sprid dims are rounded up to the nearest integer, the rounded sprid cube is larger than actual sprid cube. therefore, the threshold in calculation is lifted up to 90% in order to achieve a 85% bin fill rate using actual sprid cube. [Comment: We would initially try to achive 80% location occupany with >=85% bin fill rate. After that we will start increasing the threshold for bin fill rate to 95% or more.]

```
Example: 
Sprid A has rounded dim as 42x18x18 which gives a 85.3% bin fill rate with 2 units being stored in a 42x38x20 location.
However, actual sprid dim is 41.5x17.5x17.5 which only reaches 79.6% bin fill rate. 
Therefore, by increasing the bin fill rate threshold to 90% when identify best fit sprid dims, less locations will be under 85% target.
```

  - Max num of units per location is capped at 8
  - No double deep allowed in the rack
  - Assume boxes are being stored in the most efficient way out of total six possible orientations
  - No SKU mix, only one sprid per location
  
### 2.4 Metrics ###
  - bill fill rate (efficiency) = actual fill rate / target use rate for used locations only
  - actual fill rate = raw on hand cube / usable cube
  - target use rate (target fill rate) = usable cube / liquid cube
  - location occupation = num of used locations / num of total locations

## 3. Program Logic
### 3.1 Identify consolidation opportunities for PPL ###
  - Run on hand snapshot of PPL to find out eligible location for consolidation
    - **Partially full locations:** are the locations that already have sprid stored in. The code logic would try to determine:
      1) if the current sprid stored in this location is a best fit sprid candidate given the sprid dims and rack dims, skip if not.
      2) if the current num of sprid units stored in this location reaches the max num of units per location(f) given the sprid dims and rack dims, skip if yes.
      3) calculate the remaining num of sprid units(u) that can be consolidated into this location. 
    
    - **Empty locations:** are the locations that are empty. The code logic would try to determine:
      1) what the best fit sprid dims are for these empty locations under given criteria

  *SQL verion:* 
  [ppl_on_hand_snapshot_sql.sql](./ppl_on_hand_snapshot_sql.sql) \
  *GBQ verion:* 
  [ppl_on_hand_snapshot_gbq.sql](./ppl_on_hand_snapshot_gbq.sql)


### 3.2 Identify candidate OPL for picking ###
  - Run on hand snapshot of OPL to find out candidate sprids and locations to pick from
  
  *SQL verion:* 
  [opl_on_hand_snapshot_sql.sql](./opl_on_hand_snapshot_sql.sql) \
  *GBQ verion:* 
  [opl_on_hand_snapshot_gbq.sql](./opl_on_hand_snapshot_gbq.sql) 
  
### 3.3 Determine Pick and Putaway Logic ###

A total of 10 consolidation scenarios are identified depending on num of units on hand in candidate OPL. However, in coding the pick and putaway logic scenario 4/6/7/8 can be combined into scenario 6, and scenario 9/10 can be combined into scenario 10. See below table for details:

 - oh: available on hand best candidate sprid in OPL
 - u: required units to fill in PPL
 - comb: combination of OPLs that unit sum equals to u

Scenario # | Definition | Pick and Putaway Logic
------------ | ------------- | -------------
 1 | u = 0 | Skip
 2 | at least one opl location has oh = u | pick from rack ranking by actual fill rate asc
 3 | sum of oh < u | pick from all these opl locations
 5 | sum of oh > u, min of oh < u, no comb | pick from rack ranking by actual fill rate asc and remain excess units to empty locations, skip if no empty locations available
 6 | sum of oh > u, at least one comb | pick from racks ranking by 1) num of loc free up; 2) if 1) same, pick from the first comb; remain excess units to empty locations, skip if no empty locations available
 10 | min of oh > u | pick from racks ranking by actual fill rate, units on hand, location id asc
 

Comprehensive logic decision tree and scenarios example links:
 - [Consolidation Scenarios Decision Tree](https://drive.google.com/file/d/1aCy2wECNZsatQHUXp3IbEBD6gm29e9T3/view?usp=sharing)
 - [Consolidation Scenarios Example](https://docs.google.com/spreadsheets/d/1DVCXxv0lBwDvYPcAAMgmZY0lYMYqKx6qvtzOHiF6wZM/edit?usp=sharing)

Python code for scenario definition functions are defined in: [./scdf.py](./scdf.py)
  
### 3.4 Recalculate candidate OPL and PPL list ###  
 - Recalculate candidate OPL: after each iteration of picking, recalculate remaining units in OPL to generate candidate list for the next iteration. 
 - Recalculate PPL:
   - Partially full locations: after each iteration of putaway, recalculate the bin fill rate in PPL location that has been consolidated. 
   - Empty full locations: after each iteration of putaway, some empty location may become full or partially full, drop them from the empty full location list and append to partially full location list. when the following iterations come to them by index, the code will determine consolidation scenarios for these locations. ideally, a partially full location created by excess units overflow would have a second chance of consolidation. (<-- need to verify this)

Python code for recalc functions are defined in: [./utils.py](./utils.py) 

### 3.5 Generate output of Pick List ###
The output of the program includes:
  - Pick from location id
  - Pick sprid, huid and units
  - Putaway location id

The output for warehouse associate's use is in [Consolidation Tool V1.0](https://docs.google.com/spreadsheets/d/1KbM8WyjBJUvNUtT8y-k6VcMwV7pXafgWc9RvXncheX8/edit?usp=sharing)
  
### 3.6 How to run the code 

The main code has all modules built in but it is suggested to run each section following the sequence below:

1) run [./sprid_dims.py](./sprid_dims.py) \
This code cleans up the sprid dim data and define a function that forms a best candidate sprid dim list based on rack dims input. 

2) run [./utils.py](./utils.py) \
This code defines a set of functions that can be used for further calculation in the main code. 

3) run [./scdf.py](./scdf.py) \
This code defines all possible scenarios for consolidation. 

4) run [./prep.py](./prep.py) or [./prep2.py](./prep2.py) \
This code pull inital on hand snapshot of PPL and OPL locations as an input.  \
[./prep.py](./prep.py) is with data source from GBQ tables. Data reading from GBQ is incorporated into the python code, so no need to run the query ahead of time. \
Just for reference: [./opl_on_hand_snapshot_gbq.sql](./opl_on_hand_snapshot_gbq.sql) and [./ppl_on_hand_snapshot_gbq.sql](./ppl_on_hand_snapshot_gbq.sql). \

  [./prep2.py](./prep2.py) is with data from sql/csv tables. If choose to use [./prep2.py](./prep2.py), first run [./opl_on_hand_snapshot_sql.sql](./opl_on_hand_snapshot_sql.sql) and [./ppl_on_hand_snapshot_sql.sql](./ppl_on_hand_snapshot_sql.sql). And then save each results as csv and read into the code. 

5) run [./logic_pf.py](./logic_pf.py) \
This code runs consolidation logic for partially full locations first. 

6) run [./logic_empty.py](./logic_empty.py) \
This is the main code to run the remaining consolidatoin logic for empty locations. \
And we could schedule the code to run by a certain frequency at the bottom. \
The output of the code will be uploaded into GBQ tables. 


## 4. Performance Measurement
To measure the performance of consolidation, a total of ten metrics are defined.

 label | Metric | Definition 
------------ | ------------- | -------------
 1 | Total Liquid Cube | location liquid depth * width * height
 2 | Target Use Rate | usable cube / liquid cube
 3 | Bin Fill Rate | actual fill rate / target use rate for used locations only
 4 | Utilization | used cube / usable cube at 70% operation cap
 5 | Location Occupation | num of used location / total num of locations
 6 | SKU mixability | num of distinct SKU / num of used locations
 7 | Inventory Turnover| actual shipped units / average units on hand
 8 | Consolidation Adherence | % of suggestions are actually implemented; num of units or cube picking completed
 9 | Picking UPH | measured by site 
 10 | DMPO | measured by site 

To track performance, daily snapshots of OPL and PPL will be taken. 

**Snapshots from sqlhighjumpro:** \
python code for taking snapshots and uploading to GBQ: [./perf_metrics/sql/take_snapshots_and_load_to_gbq.py](./perf_metrics/sql/take_snapshots_and_load_to_gbq.py) \
sql for opl location sprid snapshot: [./perf_metrics/sql/opl_location_sprid_snapshot_sql.sql](./perf_metrics/sql/opl_location_sprid_snapshot_sql.sql) \
sql for opl utilization snapshot: [./perf_metrics/sql/opl_utilization_snapshot_sql.sql](./perf_metrics/sql/opl_utilization_snapshot_sql.sql) \
sql for ppl location sprid snapshot: [./perf_metrics/sql/ppl_location_sprid_snapshot_sql.sql](./perf_metrics/sql/ppl_location_sprid_snapshot_sql.sql) \
sql for ppl utilization snapshot: [./perf_metrics/sql/ppl_utilization_snapshot_sql.sql](./perf_metrics/sql/ppl_utilization_snapshot_sql.sql) \
**How to run:** manually run RSU on hand utilization script in sqlhighjumpro and run python code, the results will be uploaded into GBQ tables:



**Snapshots from GBQ:**
python code for taking snapshots and uploading to GBQ: [./perf_metrics/sql/take_snapshots_and_load_to_gbq.py](./perf_metrics/sql/take_snapshots_and_load_to_gbq.py) \
sql for opl utilization snapshot: [./perf_metrics/opl_utilization_snapshot_gbq.sql](./perf_metrics/opl_utilization_snapshot_gbq.sql) \
sql for ppl utilization snapshot: [./perf_metrics/ppl_utilization_snapshot_gbq.sql](./perf_metrics/ppl_utilization_snapshot_gbq.sql) \
**How to run:** schedule job to automatically run in Kronos 

## 5. Output Table Catalog
### 5.1 Consolidation Pick List ###

  - python output table:
  
    ```
      select * from `wf-gcp-us-ae-ops-prod.supply_chain.tbl_final_pick_list`
    ```
  - formatted output pivot for g-sheet output list refresh:
    [./final_pick_list_gbq.sql](final_pick_list_gbq.sql)

### 5.2 Performance Metric Dashboard ###

[Data studio dashboard](https://datastudio.google.com/u/0/reporting/6e8361c0-3087-48b7-854a-3fd760f4b418/page/Qd0nB)

## 6. Q & A
#### Q: How is sprid unit calculated for OPL?
  A: Sprid units for OPL are calculated based on distinct hu_id from add..t_huid_detail table instead of aad..t_stored_item as the later has time lag. For multi-box sprids, they will be considered as different boxes if their dimensions are different. For return items, they will be considered as the same box as their parent sprid. [Should we exclude return items to avoid any discrepancy?]

#### Q: How does the code logic work for excess units of a pallet?
  A: For consolidating a partially full location, each individual pick the logic will direct excess units to an available location which has the same rack dimension as the putaway location. The code will first look at if there's any partially full locations available, if not then put them to an empty location. However, for consolidating an empty location, the current logic will direct excess units to another emtpy location directly and will not look back at partially full location availability. In the next phase of code, we will improve this logic to make sure that excess units are going to partially full location first. [Comment: What happens if there are no empty locations left for leftover units?]

#### Q: How many SKU can be put into one PPL?
  A: No SKU mix allowed while generating the consolidation list. However, we found in reality, the assocates may have put different SKU in one PPL location. For now we skip these locations and they are filtered out from inital PPL list. We need to discuss with associates to prevent this from happening going forward.

#### Q: What if actual sprid dim is different from what's shown in hj?
  A: We would recommend the associate to skip these locations and send those sprids for re-measurement. Meanwhile, we'd exclude the list of incorrect sprids to prevent time waste in picking and putaway. We track incorrect sprid dims: [Potential Bad Dims Sprid List](https://docs.google.com/spreadsheets/d/1ZD-i4yD_tlzxPt3ShqPkxyvtCVCl4kImK4M8HmWxqnY/edit#gid=0)
 
```
Last Updated Date | 11/7/2020 
```

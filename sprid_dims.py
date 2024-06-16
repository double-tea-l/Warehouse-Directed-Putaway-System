# -*- coding: utf-8 -*-
"""
Created on Fri Oct 16 12:04:02 2020

@author: tl759k
"""

import pandas as pd
import numpy as np
import math
import itertools
from itertools import permutations


# Best Fit Sprid List

"""
    This code defines the best sprid dim lists of a given rack dim
    The final pilot rack dims are: 42x21x20, 42x49x20, 42x39x20 
"""

#D_r = 42
#W_r = 21
#H_r = 20
#r1 = 0.85
#inc = 1
#f = 8


class best_fit_sprid_list:
    
    def __init__(self, D_r, W_r, H_r, r1, inc, f):
        
        # inputs
        self.D_r = D_r
        self.W_r = W_r
        self.H_r = H_r
        
        self.r1 = r1
        self.inc = inc
        self.f = f
        
        # outputs
        self.sprid_dims = self.all_possible_sprid_dims()
        self.df_sprid = self.best_fit_sprid()
        

    def all_possible_sprid_dims(self):
        
        D_r = self.D_r
        W_r = self.W_r
        H_r = self.H_r
        inc = self.inc
        
        d = list(np.arange(1, D_r + 1, inc))
        w = list(np.arange(1, W_r + 1, inc))
        h = list(np.arange(1, H_r + 1, inc))
            
        # needs to deduplicate for Max, Mid, Min dims
        sprid_dims = [((str(max(d,w,h)) + 'x' + str(( d+w+h - max(d,w,h) - min(d,w,h) )) + 'x' + str(min(d,w,h))), max(d,w,h), ( d+w+h - max(d,w,h) - min(d,w,h) ), min(d,w,h) ) for d, w, h in itertools.product(d, w, h)]
        sprid_dims = pd.DataFrame(sprid_dims, columns = ['Sprid_Dims', 'MaxDim', 'MidDim', 'MinDim'])
        
        sprid_dims.drop_duplicates(inplace = True)
        sprid_dims.reset_index(drop = True)
        
        rack_dims = (str(D_r) + 'x' + str(W_r) + 'x' + str(H_r))
        
        sprid_dims['Rack_Dims'] = rack_dims
        sprid_dims['D_r'] = D_r
        sprid_dims['W_r'] = W_r
        sprid_dims['H_r'] = H_r
        
        return sprid_dims

#        sprid_dims = all_possible_sprid_dims(D_r, W_r, H_r, r1, inc)
        

    def best_fit_sprid(self):
        
        sprid_dims = self.sprid_dims
        r1 = self.r1
        f = self.f
        
        def calc(D_r, W_r, H_r, d, w, h):
        
            p = list(permutations([d,w,h], 3))   
            
            deep = [min(math.floor(D_r / i[0]), 1) for i in p]  # no double deep
            col = [math.floor(W_r / i[1]) for i in p]
            level = [math.floor(H_r/ i[2]) for i in p]
                    
            comb = [ d*c*l for d, c, l in zip(deep, col, level)]
            f = np.max(comb)
                    
            return f

        sprid_dims['f'] = np.vectorize(calc, otypes=["O"]) (sprid_dims['D_r'], sprid_dims['W_r'], sprid_dims['H_r'], sprid_dims['MaxDim'], sprid_dims['MidDim'], sprid_dims['MinDim'])   
        sprid_dims['Sprid_cube'] = sprid_dims['MaxDim'] * sprid_dims['MidDim'] * sprid_dims['MinDim'] / 1728
        sprid_dims['Rack_cube'] = sprid_dims['D_r'] * sprid_dims['W_r'] * sprid_dims['H_r'] / 1728
        sprid_dims['Util'] = sprid_dims['f'] * sprid_dims['Sprid_cube'] / sprid_dims['Rack_cube']
        #sprid_dims['f'].max()
        
        # filter best sprid dims which give bin fill rate >= e (0.85) and f limits
        sprid_dims = sprid_dims[sprid_dims['Util'] >= r1].reset_index(drop = True)
        
        # limit max num of units per loc at 8
        sprid_dims = sprid_dims[sprid_dims['f'] <= f].reset_index(drop = True)


        # sort by Util(rnk1) and f(rnk2) and then assign a rank
        df_sprid = sprid_dims.sort_values(by = ['Util', 'f'], ascending =  [False, True]) 
        #df_sprid = df_sprid.sort_values(by = ['f'], ascending = True)
        df_sprid = df_sprid.reset_index(drop = True)
        df_sprid['Rank'] = df_sprid.index + 1 # assign a rank
        df_sprid['Util/f'] = df_sprid['Util'] / df_sprid['f']
        
        df_sprid = df_sprid[['Rack_Dims', 'Sprid_Dims', 'MaxDim', 'MidDim', 'MinDim', 'D_r', 'W_r', 'H_r', 'f', 'Sprid_cube', 'Rack_cube', 'Util', 'Rank', 'Util/f']]
        
        return df_sprid
    
#s = best_fit_sprid_list(D_r, W_r, H_r, r1, inc, f)
#s.df_sprid


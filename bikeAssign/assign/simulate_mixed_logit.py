#!/usr/bin/env python

'''simulation of mixed logit
'''

from math import exp
from collections import defaultdict
from numpy import *
import numpy.random as nr

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

def simulate_mixed_logit(num_pers,predict_data,config):
    """
    This documentation refers to the fixed_coefficients case; I haven't read through the
       use_random_coefficients case (which uses the config for *mixing_granularity*)
       
    *num_pers* is the number of people to load on these paths (need not be an integer in fixed_coefficients, 
      but I don't know otherwise)
    *predict_data* is a list of dictionaries, where each dictionary corresponds to a single path
      and maps the paths variables names to their values.
    
    Returns a tuple: ([num pers on path1, num pers on path2, ...], logsum, maxutil, maxutil_components_dictionary)
      in other words, num_pers*[probability of path1, probability of path2, ...]; 
      so sum of the list is ~= num_pers
    
    Note: for random coefficients, logsum only uses the last set, probably not what you want.
    """
    
    num=num_pers
    to_load=zeros(len(predict_data))
    logsum = 0
    maxutil = -999999
    maxutil_components = defaultdict(int)
    
    while num>0:
        exputils = zeros(len(predict_data))

        for path_idx in range(len(predict_data)):
            vals=predict_data[path_idx]
            u=0
            for i in range(len(config['fixed_coefficients'])):
                u=u+config['alpha'][i]*vals[config['fixed_coefficients'][i]]
        
            if config['use_random_coefficients']:
                beta=nr.multivariate_normal(config['latent_mu'],config['latent_sigma'])
                for i in range(len(beta)):
                    beta[i]=config['random_transformations'][i](beta[i])
                    u=u+beta[i]*vals[config['random_coefficients'][i]]

            if u > maxutil: 
                maxutil = u
                maxutil_components = defaultdict(float)

                if len(config['fixed_categories'])==len(config['fixed_coefficients']):
                    for i in range(len(config['fixed_coefficients'])):
                        maxutil_components[config['fixed_categories'][i]] += config['alpha'][i]*vals[config['fixed_coefficients'][i]]
                
            exputils[path_idx]=exp(u)
            
        logsum = log(sum(exputils))         
        if num>config['mixing_granularity'] and config['use_random_coefficients']:
            to_load=to_load+config['mixing_granularity']*exputils/sum(exputils)
        else:
            to_load=to_load+num*exputils/sum(exputils)

        if config['use_random_coefficients']:
            num=num-config['mixing_granularity']
        else:
            num=0
        
    return (to_load, logsum, maxutil, maxutil_components)  
#!/usr/bin/env python

'''needs doc
'''

import random
from bikeAssign.choice_set.link_elimination import le_generate
from bikeAssign.choice_set.ds_generate import ds_generate

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

def generate_choice_set(G,chosen,choice_set_config,link_randomizer=None,time_dependent_relation=None,trip_time=None,ext_bound=None):
	
	config=choice_set_config
	
	if config['method']=='link_elimination':
		return le_generate(G,chosen,config)
		
	if config['method']=='doubly_stochastic':
		return ds_generate(G,chosen,config,link_randomizer,ext_bound,time_dependent_relation,trip_time)
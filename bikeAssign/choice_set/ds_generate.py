#!/usr/bin/env python

'''needs doc
'''

import sys,time,random
from math import log, exp,sqrt
from UserDict import UserDict
import numpy as np
from scipy.stats import gmean
from multiprocessing import Lock, Process, current_process, Queue
from bikeAssign.traversal.bidirectional_dijkstra import bidirectional_dijkstra
from bikeAssign.traversal.single_source_dijkstra import single_source_dijkstra
from bikeAssign.path_trace import path_trace
from bikeAssign.misc import get_time_dependent_variable, get_inverse_time_dependent_relation
import bikeAssign.misc as rm_misc
from bikeAssign.choice_set.link_elimination import calc_chosen_overlap

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

def ds_generate(G,chosen,choice_set_config,link_randomizer,ext_bound,time_dependent_relation=None,trip_time=None):
	
	if choice_set_config['allow_duplicates_of_chosen_route']:
		master_set=ds_generate_master(G,chosen,choice_set_config,link_randomizer,time_dependent_relation,trip_time,ext_bound)
		overlap=calc_chosen_overlap(G,chosen,master_set,choice_set_config)
		filtered_set=filter_master(G,None,master_set[1:],choice_set_config)
		return ([chosen]+filtered_set,overlap)
	else:
		return filter_master(G,chosen,ds_generate_master(G,chosen,choice_set_config,link_randomizer,time_dependent_relation,trip_time,ext_bound),choice_set_config)

def ds_generate_master(G,chosen,choice_set_config,link_randomizer,time_dependent_relation,trip_time,ext_bound):
	
	config=choice_set_config
	source=chosen[0]
	target=chosen[-1]
	
	if ext_bound is not None:
		bounding_box=ext_bound
	else:
		bounding_box=find_coef_bounding_box(G,source,target,config,time_dependent_relation,trip_time)
	
	num_draws=config['ds_num_draws']
	
	varcoef={}
	master_set=[]
	for i in range(num_draws):
		
		#sample random coefficients from bounding box
		for prelim_key in bounding_box:
			key=get_time_dependent_variable(prelim_key,trip_time,time_dependent_relation)
			if config['log_prior']:
				varcoef[key]=exp(random.uniform(log(bounding_box[prelim_key][0]),log(bounding_box[prelim_key][1])))
			else:
				varcoef[key]=random.uniform(bounding_box[prelim_key][0],bounding_box[prelim_key][1])
		
		to_iter=1
		if config['randomize_after']:
			to_iter=config['randomize_after_iters']
			
		for i in range(to_iter):
			#perform generalized cost shortest path search
			master_set.append(bidirectional_dijkstra(G,source,target,varcoef,config['weights'],link_randomizer)[1])
		
	return master_set
	
def filter_master(G,chosen,master_set,choice_set_config): # G os a TransportNetwork, chosen = ? (None here), master_set = [ path1, path2, .. ] all with the same O and D
	config=choice_set_config
	filtered=[]
	L=0
	verb=False#choice_set_config['verbose']
	if verb:
		print 'FILTERING...'
	alt=0
	chosen_hash={}
	chosen_length={}
	chosen_overlap=0.0
	
	overlap_idx=choice_set_config['overlap_var'] # e.g. 'DISTANCE'
	
	if config['randomize_after'] and config['randomize_after_iters']>1:
		random.shuffle(master_set)
	
	if chosen is None:
		the_collection=master_set
	else:
		the_collection=[chosen]+master_set

	for cur_path in the_collection:
		cur_hash={}
		cur_length=0.0
		flag=False
		if verb:
			print 'current path: ',cur_path
		if G.orig_network is None:
			R=len(cur_path)-1
		else:
			R=len(cur_path)-2
		for i in range(R):
			if verb:
				print (cur_path[i],cur_path[i+1])
			cur_hash[(cur_path[i],cur_path[i+1])]=1
			if type(cur_path[i])==type(0) and type(cur_path[i+1])==type((1,2)):
				cur_length=cur_length+G.orig_network[cur_path[i+1][0]][cur_path[i+1][1]][overlap_idx]
			else:
				cur_length=cur_length+G[cur_path[i]][cur_path[i+1]][overlap_idx]
			if verb:
				print cur_length
			if alt>0 and cur_length==0:
				flag=True
		if not flag:
			for idx in range(L):
				intersect_length=0.0
				for e in cur_hash:
					if e in filtered[idx][2]['hash']:
						if type(e[0])==type(0) and type(e[1])==type((1,2)):
							intersect_length=intersect_length+G.orig_network[e[1][0]][e[1][1]][overlap_idx]
						else:
							intersect_length=intersect_length+G[e[0]][e[1]][overlap_idx]
				if intersect_length/min(cur_length,filtered[idx][2]['length'])>=config['overlap_threshold']:
					filtered[idx][0]=filtered[idx][0]-1
					filtered.sort()
					flag=True
					break
		if not flag:
			filtered.append([0,L,{'path':cur_path,'hash':cur_hash,'length':cur_length}])
			L=L+1
			if verb:
				print 'kept'
		else:
			if verb:
				print 'removed'
		
		if chosen is not None:
			if alt==0:
				chosen_hash=cur_hash
				chosen_length=cur_length
			elif chosen_length==0:
				chosen_overlap=-1
			elif cur_length>0:
				intersect_length=0.0
				for e in cur_hash:
					if e in chosen_hash:
						if type(e[0])==type(0) and type(e[1])==type((1,2)):
							intersect_length=intersect_length+G.orig_network[e[1][0]][e[1][1]][overlap_idx]
						else:
							intersect_length=intersect_length+G[e[0]][e[1]][overlap_idx]
				chosen_overlap=max(chosen_overlap,intersect_length/chosen_length)
			alt=alt+1
	
	for item in filtered:
		item.pop(0)
	filtered.sort()
	
	result=[]

	if chosen is not None:
		assert filtered[0][1]['path']==chosen
		for item in filtered:
			result.append(item[-1]['path'])
		if config['verbose']:
			print current_process().name, '-', "filtered size: ", len(result)
		return (result,chosen_overlap)
	else:
		for item in filtered:
			result.append(item[-1]['path'])
		return result

def find_coef_bounding_box(G,source,target,choice_set_config,time_dependent_relation,trip_time):
	
	final_bound={}
	
	config=choice_set_config
	verbose=False#config['verbose']
	
	for prelim_key in config['variables']:
		
		key=get_time_dependent_variable(prelim_key,trip_time,time_dependent_relation)
		
		if key==config['ref']:
			final_bound[key]=[1,1]
			continue
		vc={config['ref']:1}
		if key in config['median_compare']:
			for compare_key in final_bound:
				if key not in config['median_compare']:
					if config['log_prior']:
						vc[compare_key]=exp( (log(final_bound[compare_key][0])+log(final_bound[compare_key][1]))/2)
					else:
						vc[compare_key]=(final_bound[compare_key][0]+final_bound[compare_key][1])/2
		
		link_randomizer=None
		if key in config['randomize_compare']:
			if not config['randomize_after']:
				raise Exception, "randomize_compare not allowed without randomize_after"
			link_randomizer=config['randomize_after_dev']
		the_seed=random.randint(0,sys.maxint)
		
		if verbose:
			print vc
		cur_wgt=None
		if key in config['weights']:
			cur_wgt=config['weights'][key]
		myfun=lambda cur_coef: path_trace(
						G,
						bidirectional_dijkstra(G,source,target,dict(vc,**{key:cur_coef}),config['weights'],link_randomizer)[1],
						key, 'sum', wgtvar=cur_wgt
						)
		
		coef_min_low = coef_min_high = log(config['ranges'][prelim_key][0])
		coef_max_low = coef_max_high = log(config['ranges'][prelim_key][1])
		val_min_low = val_min_high = myfun(exp(coef_min_low))
		val_max_low = val_max_high = myfun(exp(coef_max_low))
		if verbose:	
			print key, "coef_min_low:", exp(coef_min_low)
			print key, "coef_max_low:", exp(coef_max_low)
			print key, "val_min_low:", val_min_low
			print key, "val_max_low:", val_max_low
		
		if val_min_low == val_max_low:
			if verbose:
				print key, "no range... ignoring"
			continue
		
		if verbose:	
			print key, "coef_min_low:", exp(coef_min_low)
			print key, "coef_max_low:", exp(coef_max_low)
			print key, "val_min_low:", val_min_low
			print key, "val_max_low:", val_max_low
		
		while True:
			random.seed(the_seed)
			
			coef_mid_low = (coef_min_low+coef_max_low)/2
			coef_mid_high = (coef_min_high+coef_max_high)/2
			val_mid_low =  myfun(exp(coef_mid_low))
			val_mid_high =  myfun(exp(coef_mid_high))
			
			if verbose:
				print key, "coef_mid_low:", exp(coef_mid_low)
				print key, "coef_mid_high:", exp(coef_mid_high)
				print key, "val_mid_low:", val_mid_low
				print key, "val_mid_high:", val_mid_high
			
			if val_mid_low==val_min_low:
				coef_min_low=coef_mid_low
			else:
				coef_max_low=coef_mid_low
				val_max_low=val_mid_low
			if val_mid_high==val_max_high:
				coef_max_high=coef_mid_high
			else:
				coef_min_high=coef_mid_high
				val_min_high=val_mid_high
			
			if verbose:
				print key, "coef_low:", (exp(coef_min_low),exp(coef_max_low))
				print key, "val_low:", (val_min_low,val_max_low)
				print key, "coef_high:", (exp(coef_min_high),exp(coef_max_high))
				print key, "val_high:", (val_min_high,val_max_high)
			
			if (coef_max_low-coef_min_low)<config['tolerance']:
				break
		if coef_mid_low!=coef_mid_high:
			final_bound[key]=[exp(coef_mid_low),exp(coef_mid_high)]
	
	if verbose:
		print final_bound
	
	return final_bound

def get_extreme_bounding_box_random_sample(G,choice_set_config,time_dependent_relation,trip_times,trip_data):
	
	config=choice_set_config
	inverse_relation=get_inverse_time_dependent_relation(time_dependent_relation)
	
	id_sample=trip_data.keys()
	if config['bounding_box_sample_size']<len(trip_data):
		id_sample=random.sample(id_sample,config['bounding_box_sample_size'])
		
	all_bounds=[]
	cur_bound={}
	vars={}
	for id in id_sample:
		cur_bound=find_coef_bounding_box(G,trip_data[id][0],trip_data[id][-1],choice_set_config,time_dependent_relation,trip_times[id[0]])
		if choice_set_config['verbose']:
			print 'CUR_BOUND: ', cur_bound
		this_bound={}
		for key in cur_bound:
			orig_key=key
			if key in inverse_relation:
				orig_key=inverse_relation[key]
			this_bound[orig_key]=cur_bound[key]
			vars[orig_key]=1
		all_bounds.append(this_bound)
	
	ranges={}
	for var in vars:
		low=[]
		high=[]
		for bound in all_bounds:
			if var in bound:
				low.append(bound[var][0])
				high.append(bound[var][1])
		low.sort()
		high.sort()
			
		if low:
			low=gmean(low)
			high=gmean(high)
			if low<=high:
				ranges[var]=(low,high)
			else:
				print 'WARNING: coefficient for ' + var + ' had inconsistent high/low.  Try increasing sample size or percentile for bounding box determination.'
		else:
			print 'WARNING: coefficient for ' + var + ' had no range.  Try increasing sample size or percentile for bounding box determination.'
				
	if choice_set_config['verbose']:
		print 'EXT_BOUND: ', ranges
				
	return ranges

def bounding_box_worker(work_queue, done_queue_range,done_queue_vars,G,choice_set_config,time_dependent_relation,trip_data,trip_times):
	
	config=choice_set_config
	inverse_relation=get_inverse_time_dependent_relation(time_dependent_relation)
	
	idx=0
	vars={}
	for id in iter(work_queue.get,'STOP'):
		idx=idx+1
		cur_bound=find_coef_bounding_box(G,trip_data[id][0],trip_data[id][-1],choice_set_config,time_dependent_relation,trip_times[id[0]])
		if choice_set_config['verbose']:
			print  current_process().name, "-",idx,'CUR_BOUND: ', cur_bound
		this_bound={}
		for key in cur_bound:
			orig_key=key
			if key in inverse_relation:
				orig_key=inverse_relation[key]
			this_bound[orig_key]=cur_bound[key]
			vars[orig_key]=1
		done_queue_range.put(cur_bound)
		
	done_queue_vars.put(vars)
	done_queue_vars.put('STOP')
	done_queue_range.put('STOP')
	return True

def get_extreme_bounding_box_multithreaded(G,choice_set_config,time_dependent_relation,trip_times,trip_data,n_threads=2):
	
	config=choice_set_config
	inverse_relation=get_inverse_time_dependent_relation(time_dependent_relation)
	
	id_sample=trip_data.keys()
	if config['bounding_box_sample_size']<len(trip_data):
		id_sample=random.sample(id_sample,config['bounding_box_sample_size'])
		
	work_queue = Queue()
	done_queue_range = Queue()
	done_queue_vars=Queue()
	processes = []
		
	for trip_id in id_sample:
		work_queue.put(trip_id)

	for w in xrange(n_threads):
		p = Process(target=bounding_box_worker, args=(work_queue, done_queue_range,done_queue_vars,G,choice_set_config,time_dependent_relation,trip_data,trip_times))
		p.start()
		processes.append(p)
		work_queue.put('STOP')

	all_bounds=[]
	vars={}
	for i in range(n_threads):
		all_bounds = all_bounds + list(iter(done_queue_range.get,'STOP'))
		this_vars= list(iter(done_queue_vars.get,'STOP'))
		vars=dict(vars,**this_vars[0])
		
	for p in processes:
		p.join()
	
	ranges={}
	for var in vars:
		low=[]
		high=[]
		
		for bound in all_bounds:
			if var in bound:
				low.append(bound[var][0])
				high.append(bound[var][1])
		low.sort()
		high.sort()
			
		if low:
			low=gmean(low)
			high=gmean(high)
			if low<=high:
				ranges[var]=(low,high)
			else:
				print 'WARNING: coefficient for ' + var + ' had inconsistent high/low.  Try increasing sample size for bounding box determination.'
		else:
			print 'WARNING: coefficient for ' + var + ' had no range.  Try increasing sample size for bounding box determination.'
				
	if choice_set_config['verbose']:
		print 'EXT_BOUND: ', ranges
				
	return ranges

def ds_generate_single_source(G,source,target,choice_set_config,link_randomizer,ext_bound):
	
	config=choice_set_config
	num_draws=config['ds_num_draws']
	this_target=target
	this_link_randomizer=link_randomizer
	bounding_box=ext_bound
	
	varcoef={}
	master_sets={}
	for node in target:
		master_sets[node]=[]
		
	for i in range(num_draws):
		
		#sample random coefficients from bounding box
		for key in ext_bound:
			if config['log_prior']:
				varcoef[key]=exp(random.uniform(log(bounding_box[key][0]),log(bounding_box[key][1])))
			else:
				varcoef[key]=random.uniform(bounding_box[key][0],bounding_box[key][1])
		
		to_iter=1
		if config['randomize_after']:
			to_iter=config['randomize_after_iters']
			
		for i in range(to_iter):
		
			#perform generalized cost shortest path search
			paths = single_source_dijkstra(G,source,varcoef,target=this_target,weights=config['weights'],link_randomizer=this_link_randomizer)[1]
			for node in target:
				if node in paths:
					master_sets[node].append(paths[node])
				else:
					print 'WARNING: no path found from',str(source),'to',str(node)
	
	for node in target:
		master_sets[node]=filter_master(G,None,master_sets[node],choice_set_config)
	
	return master_sets
	

#!/usr/bin/env python

'''create a dataset to perform route choice model estimation from CycleTracks generated dataset
'''

import os, csv, sys, time, random
from math import log,exp
from optparse import OptionParser
from   multiprocessing import Lock, Process, current_process, Queue
from   transport_network import TransportNetwork, create_pseudo_dual
import bikeAssign.misc as rm_misc
import bikeAssign.input as rm_input
import bikeAssign.output as rm_output
from   bikeAssign.choice_set.generate_choice_set import generate_choice_set
import bikeAssign.choice_set.ds_generate as ds
from   bikeAssign.traversal.bidirectional_dijkstra import bidirectional_dijkstra
from   bikeAssign.choice_set.link_elimination import calc_chosen_overlap

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

def choice_set_worker(work_queue,done_queue,network,trip_data,master_config,trip_times,ext_bound):
	this_network=network

	#initialize link randomizer
	link_randomizer=None
	if master_config.choice_set_config['method']=='doubly_stochastic' and not master_config.choice_set_config['randomize_after']:
		link_randomizer=master_config.choice_set_config.get_link_randomizer(this_network,master_config)
	
		if '1' in current_process().name:
			for var in link_randomizer['variables']:
				print var," zero p: ",link_randomizer['zero']['probs'][var]
				print var," posi m: ",link_randomizer['pos']['means'][var]
	
	if master_config.choice_set_config['method']=='doubly_stochastic' and master_config.choice_set_config['randomize_after']:
		link_randomizer=master_config.choice_set_config['randomize_after_dev']
	
	idx=0
	for trip_id in iter(work_queue.get,'STOP'):
		idx=idx+1
		print time.asctime(time.localtime()), "-", current_process().name, "-",idx, ". trip_id: ", trip_id[0], ", sub_trip: ", trip_id[1], ", stage: ", trip_id[2]
		the_set,chosen_overlap=generate_choice_set(this_network,trip_data[trip_id],master_config.choice_set_config,link_randomizer,master_config['time_dependent_relation'],trip_times[trip_id[0]],ext_bound)
		done_queue.put((trip_id[0],the_set,chosen_overlap))
		
	done_queue.put('STOP')
	return True

def inverted_estimation_search_worker(work_queue,done_queue,network,trip_data,master_config,ext_bound):
	
	if not master_config.choice_set_config['randomize_after'] :
		print time.asctime(time.localtime()), "-", current_process().name, "- initializing link randomizer..."
		link_randomizer=master_config.choice_set_config.get_link_randomizer(network,master_config)
	
	rand_net=network.copy()
	rand_net.orig_network=None
	bounding_box=ext_bound
	varcoef={}
	
	"""if '1' in current_process().name:
		for var in link_randomizer['variables']:
			print var," zero p: ",link_randomizer['zero']['probs'][var]
			print var," posi m: ",link_randomizer['pos']['means'][var]
			
	print "No randomize: ", link_randomizer['no_randomize']"""
	
	for i in iter(work_queue.get,'STOP'):
		
		if master_config.choice_set_config['inverted_nested'] and not master_config.choice_set_config['randomize_after'] :
			#randomize link values
			for e in rand_net.edges_iter():
				for key in master_config.choice_set_config['variables']:
					rand_net[e[0]][e[1]][key]=link_randomizer.generate_value(network,e[0],e[1],key)
					
		#loop over number of parameter randomizations
		for j in range(master_config.choice_set_config['inverted_N_param']):
			
			print time.asctime(time.localtime()), "-", current_process().name, "- Attr #", i, ', Param #', j
			
			if not master_config.choice_set_config['inverted_nested'] and not master_config.choice_set_config['randomize_after']:
				#randomize link values
				for e in rand_net.edges_iter():
					for key in master_config.choice_set_config['variables']:
						rand_net[e[0]][e[1]][key]=link_randomizer.generate_value(network,e[0],e[1],key)			
					
			#sample generalized cost coefficients
			for key in bounding_box:
				if master_config.choice_set_config['log_prior']:
					varcoef[key]=exp(random.uniform(log(bounding_box[key][0]),log(bounding_box[key][1])))
				else:
					varcoef[key]=random.uniform(bounding_box[key][0],bounding_box[key][1])
					
			print varcoef
					
			#calculate generalized costs
			for e in rand_net.edges_iter():
				rand_net[e[0]][e[1]]['gencost']=0
				for key in varcoef:
					wgt=1
					if key in master_config.choice_set_config['weights']:
						wgt=network[e[0]][e[1]][master_config.choice_set_config['weights'][key]]
					rand_net[e[0]][e[1]]['gencost']=rand_net[e[0]][e[1]]['gencost']+varcoef[key]*rand_net[e[0]][e[1]][key]*wgt
			
			use_cost='gencost'
			to_iter=1
			if master_config.choice_set_config['randomize_after']:
				use_cost='usecost'
				to_iter=master_config.choice_set_config['randomize_after_iters']
				
			while to_iter:
				to_iter=to_iter-1
				result_paths={}
				
				if master_config.choice_set_config['randomize_after']:
					for e in rand_net.edges_iter():
						rand_net[e[0]][e[1]]['usecost']=rand_net[e[0]][e[1]]['gencost']*random.uniform(1-master_config.choice_set_config['randomize_after_dev'],1+master_config.choice_set_config['randomize_after_dev'])
					
				for trip_id in trip_data.keys():
				
					source=trip_data[trip_id][0]
					target=trip_data[trip_id][-1]
				
					#add gateways
					if network.orig_network is not None:
						for neighbor in network.orig_network.successors_iter(source):
							new_data=dict(network.orig_network[source][neighbor],**{use_cost:0})
							for key in varcoef:
								if key not in ['TURN','L_TURN','R_TURN','U_TURN']:
									wgt=1
									if key in master_config.choice_set_config['weights']:
										wgt=new_data[master_config.choice_set_config['weights'][key]]
									new_data[use_cost]=new_data[use_cost]+varcoef[key]*new_data[key]*wgt
							rand_net.add_edge(source,(source,neighbor),new_data)
						for neighbor in network.orig_network.predecessors_iter(target):
							rand_net.add_edge((neighbor,target),target,{use_cost:0})
						
					result_paths[trip_id]=bidirectional_dijkstra(rand_net,source,target,use_cost)[1]
				
					#remove gateways
					if network.orig_network is not None:
						for neighbor in network.orig_network.successors_iter(source):
							rand_net.remove_edge(source,(source,neighbor))
						for neighbor in network.orig_network.predecessors_iter(target):
							rand_net.remove_edge((neighbor,target),target)
						
				done_queue.put(result_paths)
	
	done_queue.put('STOP')
	return True
	
def inverted_estimation_filter_worker(work_queue,done_queue,G,master_sets,choice_set_config):
	
	for trip_id in iter(work_queue.get,'STOP'):
		if choice_set_config['allow_duplicates_of_chosen_route']:
			chosen_overlap=calc_chosen_overlap(G,master_sets[trip_id][0],master_sets[trip_id][1:],choice_set_config)
			choice_set=ds.filter_master(G,None,master_sets[trip_id][1:],choice_set_config)
			choice_set=[master_sets[trip_id][0]]+choice_set
			done_queue.put((trip_id,choice_set,chosen_overlap))
		else:
			choice_set,chosen_overlap=ds.filter_master(G,master_sets[trip_id][0],master_sets[trip_id][1:],choice_set_config)
			done_queue.put((trip_id,choice_set,chosen_overlap))

	done_queue.put('STOP')
	return True

if __name__ == '__main__':
	
	parser=OptionParser()
	parser.add_option("-m", dest="master_config",help="python path to master configuration module")
	(options, args)=parser.parse_args()
	
	print time.asctime(time.localtime())
	
	mandatory=['master_config']
	for m in mandatory:
		if not options.__dict__[m]:
			parser.print_help()
			sys.exit()
			
	#set up
	master_config=rm_misc.get_class_instance_from_python_path(options.master_config)
	prelim_network=TransportNetwork(master_config.network_config)
	
	#exclude links
	if 'exclude_group' in master_config.network_config:
		for variable in master_config.network_config['exclude_group']:
			exclude=prelim_network.select_edges_where(variable,master_config.network_config['exclude_group'][variable][0],master_config.network_config['exclude_group'][variable][1],False)
			prelim_network.remove_edges_from(exclude)
	
	#read data
	if 'trip_file' in master_config:
		trip_data=rm_input.read_trip_data(master_config['trip_file'])
	else:
		trip_data=rm_input.read_trip_data_from_matsim(master_config['travel_dir'])
	trip_times=rm_input.read_time(master_config['time_file'])
	
	print "number of trips: ", len(trip_data.keys())
	
	#create pseudo_dual
	network=prelim_network
	if 'use_dual' in master_config.network_config:
		if master_config.network_config['use_dual']:
			network=create_pseudo_dual(prelim_network)
			for id in trip_data:
				trip_data[id]=rm_misc.get_dual_path(trip_data[id])
			del prelim_network
				
	#extract ds coefficient bounding box
	ext_bound=None
	if master_config.choice_set_config['method']=='doubly_stochastic' and master_config.choice_set_config['ext_bound']:
		if master_config.choice_set_config['bound_from_file']:
			ext_bound,master_config.choice_set_config['weights'],master_config.choice_set_config['ranges']=rm_input.read_bound(master_config.choice_set_config['bound_file'],return_ranges=True)
			del_keys=[]
			if master_config.choice_set_config['bound_file_override']==True:
				master_config.choice_set_config['variables']=ext_bound.keys()
			else:
				for key in ext_bound:
					if key not in master_config.choice_set_config['variables']:
						del_keys.append(key)
				for key in del_keys:
					del ext_bound[key]
			print 'EXT_BOUND: ', ext_bound
		else:
			if master_config['n_processes']>1:
				ext_bound=ds.get_extreme_bounding_box_multithreaded(network,master_config.choice_set_config,master_config['time_dependent_relation'],trip_times,trip_data,master_config['n_processes'])
			else:
				ext_bound=ds.get_extreme_bounding_box_random_sample(network,master_config.choice_set_config,master_config['time_dependent_relation'],trip_times,trip_data)
	
	#set up time-dependent variables
	if master_config.choice_set_config['method']=='doubly_stochastic':
		for var in master_config['time_dependent_relation']:
			if var in master_config.choice_set_config['variables']:
				if master_config.choice_set_config['inverted']:
					raise Exception, 'Time-dependent variables not supported with inverted randomization and search'
				for rule in master_config['time_dependent_relation'][var]:
					master_config.choice_set_config['weights'][rule[1]]=master_config.choice_set_config['weights'][var]
		
	#create_holdback_sample
	holdback_rate=0.0
	holdback_sample=set()
	if master_config['use_holdback_sample']:
		if not master_config['holdback_from_file']:
			holdback_rate=master_config['holdback_rate']
			for id in trip_data:
				if random.random()<holdback_rate:
					holdback_sample.add(id[0])
		else:
			holdback_sample=rm_input.read_holdback(master_config['holdback_file'])
	to_delete=[]
	for id in trip_data:
		if id[0] in holdback_sample:
			to_delete.append(id)
	for id in to_delete:
		del trip_data[id]
	
	if not master_config.choice_set_config['only_bound']:
		
		if master_config.choice_set_config['inverted'] and master_config.choice_set_config['method']=='doubly_stochastic':
			
			work_queue = Queue()
			done_queue = Queue()
			processes = []			
			
			for i in range(master_config.choice_set_config['inverted_N_attr']):
				work_queue.put(i)
		
			for w in xrange(master_config['n_processes']):
				p = Process(target=inverted_estimation_search_worker, args=(work_queue, done_queue,network,trip_data,master_config,ext_bound))
				p.start()
				processes.append(p)
				work_queue.put('STOP')
				
			result=[]
			for i in range(master_config['n_processes']):
				result = result + list(iter(done_queue.get,'STOP'))
			
			for p in processes:
				p.join()
				
			master_sets={}
			for id in trip_data.keys():
				master_sets[id]=[trip_data[id]]
				
			for path_collection in result:
				for id in path_collection:
					master_sets[id].append(path_collection[id])
					
			work_queue = Queue()
			done_queue = Queue()
			processes = []			
			
			for id in trip_data.keys():
				work_queue.put(id)
			
			for w in xrange(master_config['n_processes']):
				p = Process(target=inverted_estimation_filter_worker, args=(work_queue, done_queue,network,master_sets,master_config.choice_set_config))
				p.start()
				processes.append(p)
				work_queue.put('STOP')
			
			result=[]
			for i in range(master_config['n_processes']):
				result = result + list(iter(done_queue.get,'STOP'))
		
			for p in processes:
				p.join()
	
			trip_ids=[]
			choice_sets=[]
			chosen_overlap=[]
			for the_id, the_set, the_overlap in result:
				trip_ids.append(the_id[0])
				choice_sets.append(the_set)
				chosen_overlap.append(the_overlap)

		else:
		
			#generate choice sets
			work_queue = Queue()
			done_queue = Queue()
			processes = []
			
	
			for trip_id in trip_data.keys():
				work_queue.put(trip_id)

			for w in xrange(master_config['n_processes']):
				p = Process(target=choice_set_worker, args=(work_queue, done_queue,network,trip_data,master_config,trip_times,ext_bound))#,network,trip_data,master_config,link_randomizer,trip_times,ext_bound))
				p.start()
				processes.append(p)
				work_queue.put('STOP')

			result=[]
			for i in range(master_config['n_processes']):
				result = result + list(iter(done_queue.get,'STOP'))
			
			for p in processes:
				p.join()
			
			trip_ids=[]
			choice_sets=[]
			chosen_overlap=[]
			for item in result:
				trip_ids.append(item[0])
				choice_sets.append(item[1])
				chosen_overlap.append(item[2])
	
	#output
	master_config.output_config.setup_files()
	
	if not master_config.choice_set_config['only_bound']:
				
		if 'estimation' in master_config.output_config['output_type']:
			rm_output.create_estimation_dataset(network,choice_sets,trip_ids,trip_times,master_config)
			
		if 'overlap' in master_config.output_config['output_type']:
			rm_output.create_csv_from_overlap(trip_ids,chosen_overlap,master_config)
			
		if 'geographic' in master_config.output_config['output_type']:
			rm_output.create_csv_from_choice_sets(choice_sets,trip_ids,master_config.output_config['pathID'],master_config.output_config['pathLink'])
		
		if 'holdback_sample' in master_config.output_config['output_type']:
			rm_output.create_csv_from_holdback_sample(master_config,holdback_sample)
		
	if 'bound' in master_config.output_config['output_type'] and ext_bound:
		rm_output.create_csv_from_ext_bound(master_config,ext_bound)
		

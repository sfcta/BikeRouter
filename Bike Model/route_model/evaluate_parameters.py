import os, csv, sys
from optparse import OptionParser
import route_model.misc as rm_misc
import route_model.input as rm_input
import route_model.output as rm_output
from transport_network import TransportNetwork, create_pseudo_dual
from route_model.choice_set.generate_choice_set import generate_choice_set
import route_model.choice_set.ds_generate as ds
import time
from multiprocessing import Lock, Process, current_process, Queue
import random
import numpy


def param_worker(work_queue,done_queue,network,trip_data,master_config,trip_times,ext_bound,trip_ids):
	
	this_network=network.copy()
	
	#initialize link randomizer
	link_randomizer=None
	if master_config.choice_set_config['method']=='doubly_stochastic':
		link_randomizer=master_config.choice_set_config.get_link_randomizer(network,master_config)
	
	for kappa, sigma in iter(work_queue.get,'STOP'):

		link_randomizer.set_scl(kappa)
		link_randomizer.set_par(link_randomizer['zero']['par'],[1-sigma,1+sigma])
		link_randomizer.update_denoms()
		
		random.seed(0)
		idx=0
		overlap_sum=0
		for trip_id in trip_ids:
			idx=idx+1
			print time.asctime(time.localtime()), "-", current_process().name, "-",idx, ", k: ", kappa, ", s: ", sigma ,". trip_id: ", trip_id[0], ", sub_trip: ", trip_id[1], ", stage: ", trip_id[2]
			the_set,chosen_overlap=generate_choice_set(this_network,trip_data[trip_id],master_config.choice_set_config,link_randomizer,master_config['time_dependent_relation'],trip_times[trip_id[0]],ext_bound)
			overlap_sum=overlap_sum+chosen_overlap
		
		done_queue.put((kappa,sigma,overlap_sum/idx))
		
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
	
	#create pseudo_dual
	network=prelim_network
	if 'use_dual' in master_config.network_config:
		if master_config.network_config['use_dual']:
			network=create_pseudo_dual(prelim_network)
			for id in trip_data:
				trip_data[id]=rm_misc.get_dual_path(trip_data[id])
	
	#extract ds coefficient bounding box
	ext_bound=None
	if master_config.choice_set_config['method']=='doubly_stochastic' and master_config.choice_set_config['ext_bound']:
		if master_config.choice_set_config['bound_from_file']:
			ext_bound,master_config.choice_set_config['weights']=rm_input.read_bound(master_config.choice_set_config['bound_file'])
			del_keys=[]
			for key in ext_bound:
				if key not in master_config.choice_set_config['variables']:
					del_keys.append(key)
			for key in del_keys:
				del ext_bound[key]
		else:
			ext_bound=ds.get_extreme_bounding_box_random_sample(network,master_config.choice_set_config,master_config['time_dependent_relation'],trip_times,trip_data,master_config.choice_set_config['bound_percentile'])
	
	#set up time-dependent variables
	if master_config.choice_set_config['method']=='doubly_stochastic':
		for var in master_config['time_dependent_relation']:
			if var in master_config.choice_set_config['variables']:
				for rule in master_config['time_dependent_relation'][var]:
					master_config.choice_set_config['weights'][rule[1]]=master_config.choice_set_config['weights'][var]
	
	param_list=[(k,s) for k in master_config.choice_set_config['optim_kappa_vals'] for s in master_config.choice_set_config['optim_sigma_vals']]
	
	random.seed(0)
	
	f=open(master_config['imperfect_file'],'rU')
	reader=csv.reader(f)
	imperfect={}
	for row in reader:
		imperfect[row[0]]=1
	f.close()
	
	trip_ids=trip_data.keys()
	final_ids=[]
	for id in trip_ids:
		if id[0] in imperfect:
			final_ids.append(id)
			
	id_samp=random.sample(final_ids,master_config.choice_set_config['optim_sample_size'])
	
	processes = []
	work_queue=Queue()
	done_queue=Queue()
	
	for param in param_list:
		work_queue.put(param)

	for w in xrange(master_config['n_processes']):
		p = Process(target=param_worker, args=(work_queue,done_queue,network,trip_data,master_config,trip_times,ext_bound,id_samp))
		p.start()
		processes.append(p)
		work_queue.put('STOP')


	result=[]
	for i in range(master_config['n_processes']):
		result = result + list(iter(done_queue.get,'STOP'))
			
	for p in processes:
		p.join()
			
	for item in result:
		print item
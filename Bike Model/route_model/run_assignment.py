import os, csv, sys, glob
from optparse import OptionParser
import route_model.misc as rm_misc
import route_model.input as rm_input
import route_model.output as rm_output
from transport_network import TransportNetwork, create_pseudo_dual
from route_model.choice_set.generate_choice_set import generate_choice_set
import route_model.choice_set.ds_generate as ds
from route_model.assign.project_outer_trips import project_outer_trips
import time
from multiprocessing import Lock, Process, current_process, Queue, Manager
from route_model.choice_set.path_size import path_size
from route_model.assign.simulate_mixed_logit import simulate_mixed_logit
from math import log,exp
from route_model.path_trace import path_trace
import random
from route_model.traversal.single_source_dijkstra import single_source_dijkstra
import cPickle, glob

def trace_and_load(network,filtered_sets,master_config,matrix_list,source):
	config=master_config.assign_config
	this_network=network

	#trace
	print current_process().name, "- zone: ", source, "Tracing paths..."
	predict_collection={}
	for target in filtered_sets:
		predict_data=[]
		for path in filtered_sets[target]:
			trace_vals={}
			for i in range(len(config['variables'])):
				var=config['variables'][i]
				trace_vals[config['aliases'][i]]=path_trace(this_network,path,var,config['trace_funs'][i],config['final_funs'][i],config['weights'][i])
			for var in trace_vals:	
				if var in config['divisors']:
					trace_vals[var]=trace_vals[var]/trace_vals[config['divisors'][var]]
			predict_data.append(trace_vals)
		if config['path_size']:
			PS=path_size(this_network,[filtered_sets[target]],master_config.choice_set_config).pop()
			for i in range(len(filtered_sets[target])):
				if config['path_size_log']:
					PS[i]=log(PS[i])
				predict_data[i][config['path_size_alias']]=PS[i]
		predict_collection[target]=predict_data
	
	#apply logit probabilities
	print current_process().name, "- zone: ", source, "Applying logit probabilities..."
	
	to_load=[]
	for mat_idx in range(len(matrix_list)):
		to_load.append({})
		for target in predict_collection:
			num_pers=matrix_list[mat_idx][source-1,target-1]
			to_load[mat_idx][target]=simulate_mixed_logit(num_pers,predict_collection[target],config)
	
	#load onto network
	print current_process().name, "- zone: ", source, "Loading network..."
	for target in filtered_sets:
		for j in range(len(filtered_sets[target])):
			path=filtered_sets[target][j]
			if this_network.orig_network is None:
				for i in range(len(path)-1):
					for mat_idx in  range(len(matrix_list)):
						this_network[path[i]][path[i+1]][config['load_names'][mat_idx]]=this_network[path[i]][path[i+1]][config['load_names'][mat_idx]]+to_load[mat_idx][target][j]
			else:
				for i in range(1,len(path)-1):
					for mat_idx in  range(len(matrix_list)):
						this_network.orig_network[path[i][0]][path[i][1]][config['load_names'][mat_idx]]=this_network.orig_network[path[i][0]][path[i][1]][config['load_names'][mat_idx]]+to_load[mat_idx][target][j]

def assign_worker(work_queue,done_queue,network,master_config,ext_bound,matrix):
	this_network=network
	config=master_config.assign_config
	
	#initialize link randomizer
	link_randomizer=None
	if master_config.choice_set_config['method']=='doubly_stochastic' and not master_config.choice_set_config['randomize_after']:
		print time.asctime(time.localtime()), "-", current_process().name, "Initializing link randomizer..."
		link_randomizer=master_config.choice_set_config.get_link_randomizer(this_network,master_config)
	
	if master_config.choice_set_config['method']=='doubly_stochastic' and master_config.choice_set_config['randomize_after']:
		link_randomizer=master_config.choice_set_config['randomize_after_dev']
	
	idx=0
	for source,the_target in iter(work_queue.get,'STOP'):
		idx=idx+1
		print time.asctime(time.localtime()), "-", current_process().name, "-",idx, ". zone: ", source, "Generating sets..."
		
		if source in the_target:
			del the_target[source]
		
		filtered_sets=ds.ds_generate_single_source(this_network,source,the_target,master_config.choice_set_config,link_randomizer,ext_bound)
		
		trace_and_load(this_network,filtered_sets,master_config,matrix,source)
	
	done_queue.put(this_network.orig_network)
	done_queue.put('STOP')
	return True

def inverted_assignment_search_worker(work_queue,done_queue,network,master_config,ext_bound,st_dict,seed_selections):
	
	if not master_config.choice_set_config['randomize_after'] :
		print time.asctime(time.localtime()), "-", current_process().name, "- initializing link randomizer..."
		link_randomizer=master_config.choice_set_config.get_link_randomizer(network,master_config)
	
	rand_net=network.copy()
	rand_net.orig_network=None
	bounding_box=ext_bound
	varcoef={}
	
	for i in iter(work_queue.get,'STOP'):
		
		if master_config.choice_set_config['inverted_nested'] and not master_config.choice_set_config['randomize_after']:
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

				for source in st_dict:
				
					if seed_selections[source][i*master_config.choice_set_config['inverted_N_param']+j]:
						the_target=st_dict[source]
				
						if source in the_target:
							del the_target[source]
					
						every_path=single_source_dijkstra(rand_net,source,use_cost,target=the_target)[1]
				
						target_paths={}
						for t in the_target:
							if t in every_path:
								target_paths[t]=every_path[t]
				
						fname=os.path.join(master_config.assign_config['pickle_path'],str(source)+'_'+str(i)+'-'+str(j)+'_'+str(to_iter))
						f=open(fname,'wb')
						cPickle.dump(target_paths,f,1)
						f.close()
			
	done_queue.put('STOP')
	return True
	
def inverted_assignment_load_worker(work_queue,done_queue,network,master_config,ext_bound,matrix_list):
	this_network=network
	config=master_config.assign_config
	
	idx=0
	for source,the_target in iter(work_queue.get,'STOP'):
		idx=idx+1
		print time.asctime(time.localtime()), "-", current_process().name, "-",idx, ". zone: ", source, "Selecting random sample of generated paths..."
		
		if source in the_target:
			del the_target[source]
		
		master_sets={}
		for t in the_target:
			master_sets[t]=[]
		to_iter=1
		if master_config.choice_set_config['randomize_after']:
			to_iter=master_config.choice_set_config['randomize_after_iters']
		while to_iter:
			to_iter=to_iter-1
			for fname in glob.glob(os.path.join(master_config.assign_config['pickle_path'],str(source)+'_*')):
				f=open(fname,'rb')
				target_paths=cPickle.load(f)
				f.close()
				for t in the_target:
					if t in target_paths:
						master_sets[t].append(target_paths[t])
		
		filtered_sets={}
		for t in master_sets:
			if master_sets[t]!=[]:
				#filter master set
				filtered_sets[t]=ds.filter_master(this_network,None,master_sets[t],master_config.choice_set_config)
			
		trace_and_load(this_network,filtered_sets,master_config,matrix_list,source)
	
	done_queue.put(this_network.orig_network)
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
	print "Reading matrices...",
	matrix_list=[]
	for filename in master_config.assign_config['matrix_filenames']:
		matrix_list.append(rm_input.read_matrix(filename))
	print "Done."
	
	#delete old path files
	if not master_config.assign_config['load_paths_from_files']:
		print "Deleting old path files...",
		for f in glob.glob(os.path.join(master_config.assign_config['pickle_path'], '*')):
			os.remove(f)
		print "Done."
	
	#project outer trips
	print "Reading outer network...",
	outer_network=TransportNetwork(master_config.outer_network_config)
	print "Done."
	print "Projecting outer trips...",
	for mat in matrix_list:
		mat=project_outer_trips(outer_network,mat,master_config.assign_config)
	del outer_network
	print "Done."
	
	print "Setting up inner network...",
	prelim_network=TransportNetwork(master_config.network_config)
	for e in prelim_network.edges_iter(data=True):
		for load_name in master_config.assign_config['load_names']:
			e[2][load_name]=0
	
	#exclude links
	if 'exclude_group' in master_config.network_config:
		for variable in master_config.network_config['exclude_group']:
			exclude=prelim_network.select_edges_where(variable,master_config.network_config['exclude_group'][variable][0],master_config.network_config['exclude_group'][variable][1],False)
			prelim_network.remove_edges_from(exclude)
	
	#create pseudo_dual
	network=prelim_network
	if 'use_dual' in master_config.network_config:
		if master_config.network_config['use_dual']:
			network=create_pseudo_dual(prelim_network)
			network.make_centroid_gateways()
	print "Done."
	
	#read ds coefficient bounding box
	ext_bound,master_config.choice_set_config['weights'],master_config.choice_set_config['ranges']=rm_input.read_bound(master_config.assign_config['bound_file'],return_ranges=True)
	del_keys=[]
	if master_config.choice_set_config['bound_file_override']==True:
		master_config.choice_set_config['variables']=ext_bound.keys()
	else:
		for key in ext_bound:
			if key not in master_config.choice_set_config['variables']:
				del_keys.append(key)
		for key in del_keys:
			del ext_bound[key]
	
	#time-dependent variables not supported for assignment
	if master_config.choice_set_config['method']=='doubly_stochastic':
		for var in master_config.choice_set_config['variables']:
			if var in master_config['time_dependent_relation'] :
				raise Exception, 'Time-dependent variables not supported for assignment'
	
	if master_config.assign_config['test_small_matrix']:
		from_range=range(4)
	else:
		from_range=range(master_config.assign_config['max_inner'])
	to_range=range(master_config.assign_config['max_inner'])
	
	if master_config.choice_set_config['inverted'] and master_config.choice_set_config['method']=='doubly_stochastic':
		
		#perform initial searches
		work_queue = Queue()
		done_queue = Queue()
		processes = []
		
		"""mgr=Manager()
		ns=mgr.Namespace()
		ns.network=network"""

    # st_dict = source target dictionary		
		st_dict={}
		for i in from_range:
			the_target={}
			for j in to_range:
				for mat in matrix_list:
					if mat[i,j]>0 and i!=j:
						the_target[j+1]=1
			st_dict[i+1]=the_target
		
		num_link_seeds=int(master_config.choice_set_config['inverted_N_attr']*master_config.assign_config['inverted_multiple'])
		samp_size=master_config.choice_set_config['inverted_N_attr']*master_config.choice_set_config['inverted_N_param']
		num_full_seeds=int(samp_size*master_config.assign_config['inverted_multiple'])
		seed_selections={}
		select_from=[1]*samp_size+[0]*(num_full_seeds-samp_size)
		for source in st_dict:
			random.shuffle(select_from)
			seed_selections[source]=list(select_from)
			#print seed_selections[source]
		
		if not master_config.assign_config['load_paths_from_files']:
		
			for i in range(num_link_seeds):
				work_queue.put(i)
		
			for w in xrange(master_config['n_processes']):
				p = Process(target=inverted_assignment_search_worker, args=(work_queue, done_queue,network,master_config,ext_bound,st_dict,seed_selections))
				p.start()
				processes.append(p)
				work_queue.put('STOP')
			
			result=[]
			for i in range(master_config['n_processes']):
				result = result + list(iter(done_queue.get,'STOP'))
			del result
		
			for p in processes:
				p.join()
		
		"""
		mgr.shutdown()
		"""
		
		#load network
		work_queue = Queue()
		done_queue = Queue()
		processes = []
		
		for source in st_dict:
			work_queue.put((source,st_dict[source]))
			
		for w in xrange(master_config['n_processes']):
			p = Process(target=inverted_assignment_load_worker, args=(work_queue, done_queue,network,master_config,ext_bound,matrix_list))
			p.start()
			processes.append(p)
			work_queue.put('STOP')
	
	else:
		#perform initial searches
		print "Creating child processes..."
		work_queue = Queue()
		done_queue = Queue()
		processes = []
		
		for i in from_range:
			the_target={}
			for j in to_range:
				for mat in matrix_list:
					if mat[i,j]>0 and i!=j:
						the_target[j+1]=1
			work_queue.put((i+1,the_target))
		
		for w in xrange(master_config['n_processes']):
			p = Process(target=assign_worker, args=(work_queue, done_queue,network,master_config,ext_bound,matrix))
			p.start()
			processes.append(p)
			work_queue.put('STOP')

	#combine loads from different processes
	net_list=[]
	for i in range(master_config['n_processes']):
		net_list = net_list + list(iter(done_queue.get,'STOP'))
			
	for p in processes:
		p.join()
	
	if master_config.assign_config['delete_paths']:
		for f in glob.glob(os.path.join(master_config.assign_config['pickle_path'], '*')):
			os.remove(f)

	print 'combining loads...'
	
	final_net=net_list.pop()
	for e in final_net.edges_iter(data=True):
		for i in range(len(net_list)):
			for mat_idx in range(len(matrix_list)):
				final_net[e[0]][e[1]][master_config.assign_config['load_names'][mat_idx]] \
					=final_net[e[0]][e[1]][master_config.assign_config['load_names'][mat_idx]] \
					+ net_list[i][e[0]][e[1]][master_config.assign_config['load_names'][mat_idx]]
	
	print 'writing output file...'
	
	#output
	master_config.output_config.setup_files()
	
	if 'assign' in master_config.output_config['output_type']:
		rm_output.create_csv_from_assignment(final_net,master_config)
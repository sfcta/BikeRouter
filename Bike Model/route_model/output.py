import csv
from route_model.path_trace import path_trace
from route_model.choice_set.path_size import path_size
from route_model.misc import get_time_dependent_variable, get_orig_path
import copy

def create_csv_from_path_list(path_list,pathname,linkname,dataNames=[],dataFrame=None):
	"""create two linked csv tables containing path links and path ids for viewing in GIS"""
	
	linkfile=open(linkname,'w')
	link_writer=csv.writer(linkfile,lineterminator='\r')
	
	pathfile=open(pathname,'w')
	path_writer=csv.writer(pathfile,lineterminator='\r')
	
	link_writer.writerow(['link_id','path_id','a','b'])
	path_writer.writerow(['path_id','orig','dest']+dataNames)
	
	for i in range(len(path_list)):
		curpath=path_list[i]
		if dataFrame is not None:
			temp=list(dataFrame[i])
		else:
			temp=[]
		path_writer.writerow([str(i),curpath[0],curpath[-1]]+temp)
		for j in range(len(curpath)-1):
			link_writer.writerow([str(j),str(i),curpath[j],curpath[j+1]])
	
	linkfile.close() 
	pathfile.close()
	
def create_csv_from_choice_sets(choice_sets,trip_ids,pathname,linkname):
	"""create two linked csv tables containing path links and path ids for viewing in GIS"""
	
	linkfile=open(linkname,'w')
	link_writer=csv.writer(linkfile,lineterminator='\r')
	
	pathfile=open(pathname,'w')
	path_writer=csv.writer(pathfile,lineterminator='\r')
	
	link_writer.writerow(['link_id','occ_id','trip_id','path_id','a','b'])
	path_writer.writerow(['occ_id','trip_id','path_id','orig','dest'])
	
	for k in range(len(choice_sets)):
		curset=choice_sets[k]
		for i in range(len(curset)):
			prelimpath=curset[i]
			if type(prelimpath[1])==type((1,2)):
				curpath=get_orig_path(prelimpath)
			else:
				curpath=prelimpath
			path_writer.writerow([str(k),trip_ids[k],str(i),curpath[0],curpath[-1]])
			for j in range(len(curpath)-1):
				link_writer.writerow([str(j),str(k),trip_ids[k],str(i),curpath[j],curpath[j+1]])
	
	linkfile.close() 
	pathfile.close()

def create_estimation_dataset(G,path_list_collection,id_list,trip_times,master_config):
	
	output_config=master_config.output_config
	choice_set_config=master_config.choice_set_config
	
	est_file=open(output_config['estimation_data'],'w')
	est_writer=csv.writer(est_file,lineterminator='\r')
	
	if output_config['path_size']:
		path_size_alias=['path_size']
	else:
		path_size_alias=[]
	
	est_writer.writerow(['occ','alt','trip_id','chosen']+output_config['aliases']+path_size_alias)
	
	path_size_data=path_size(G,path_list_collection,choice_set_config)
	
	for occ_idx in range(len(path_list_collection)):
		for alt_idx in range(len(path_list_collection[occ_idx])):
			path=path_list_collection[occ_idx][alt_idx]
			values=[]
			for i in range(len(output_config['variables'])):
				if output_config['variables'][i] in master_config['time_dependent_relation']:
					key=get_time_dependent_variable(output_config['variables'][i],trip_times[id_list[occ_idx]],master_config['time_dependent_relation'])
				else:
					key=output_config['variables'][i]
				values.append(str(path_trace(G,path,key,output_config['trace_funs'][i],output_config['final_funs'][i],output_config['weights'][i])))
			if output_config['path_size']:
				values.append(path_size_data[occ_idx][alt_idx])
			est_writer.writerow([str(occ_idx),str(alt_idx),str(id_list[occ_idx]),str(alt_idx==0)]+values)
	
	est_file.close()
	
def create_csv_from_ext_bound(master_config,ext_bound):
	
	output_config=master_config.output_config
	choice_set_config=master_config.choice_set_config
	
	bound_file=open(output_config['bound_data'],'w')
	bound_writer=csv.writer(bound_file)
	
	bound_writer.writerow(['variable','weight','init_low','init_high','final_low','final_high'])
	
	for key in choice_set_config['variables']:
		weight='None'
		if key in choice_set_config['ranges'] and key in ext_bound:
			if key in choice_set_config['weights']:
				weight=choice_set_config['weights'][key]
			init_low=choice_set_config['ranges'][key][0]
			init_high=choice_set_config['ranges'][key][1]
			final_low=ext_bound[key][0]
			final_high=ext_bound[key][1]
		elif key not in choice_set_config['ranges'] and key in ext_bound:
			weight='None'
			init_low=1
			init_high=1
			final_low=ext_bound[key][0]
			final_high=ext_bound[key][1]
		elif key in choice_set_config['ranges']:
			if key in choice_set_config['weights']:
				weight=choice_set_config['weights'][key]
			init_low=choice_set_config['ranges'][key][0]
			init_high=choice_set_config['ranges'][key][1]
			final_low=0
			final_high=0
		else:
			continue
			
		bound_writer.writerow([key,weight,init_low,init_high,final_low,final_high])	
		
	
	bound_file.close()
	
def create_csv_from_overlap(trip_ids,chosen_overlap,master_config):
	
	output_config=master_config.output_config
	
	overlap_file=open(output_config['overlap_data'],'w')
	overlap_writer=csv.writer(overlap_file,lineterminator='\r')
	
	overlap_writer.writerow(['occ','trip_id','overlap'])
	for occ_idx in range(len(trip_ids)):
		overlap_writer.writerow([str(occ_idx),str(trip_ids[occ_idx]),str(chosen_overlap[occ_idx])])
		
	overlap_file.close()
	
def create_csv_from_matrix(matrix,master_config,name=""):
	
	output_config=master_config.output_config
	
	matrix_file=open(output_config['matrix_data'],'w')
	matrix_writer=csv.writer(matrix_file,lineterminator='\r')
	
	matrix_writer.writerow([name]+range(1,matrix.shape[0]+1))
	for i in range(matrix.shape[0]):
		matrix_writer.writerow([i+1]+list(matrix[i,:]))
		
	matrix_file.close()
	
def create_csv_from_assignment(network,master_config):
	
	output_config=master_config.output_config
	
	file=open(output_config['assign_data'],'w')
	writer=csv.writer(file,lineterminator='\r')
	
	writer.writerow(['A','B']+master_config.assign_config['load_names'])
	for e in network.edges_iter(data=True):
		the_data=[e[0],e[1]]
		for load_name in master_config.assign_config['load_names']:
			the_data.append(e[2][load_name])
		writer.writerow(the_data)
		
	file.close()

def create_csv_from_holdback_sample(master_config,holdback_sample):
	
	output_config=master_config.output_config
	
	holdback_file=open(output_config['holdback_file'],'w')
	holdback_writer=csv.writer(holdback_file,lineterminator='\r')
	
	holdback_writer.writerow(['trip_id'])
	for trip_id in holdback_sample:
		holdback_writer.writerow([trip_id])
		
	holdback_file.close()
	
def create_holdback_prediction_dataset(G,path_list_collection,id_list,trip_times,master_config,chosen_overlap):
	
	output_config=master_config.output_config
	choice_set_config=master_config.choice_set_config
	
	est_file=open(output_config['estimation_data'],'w')
	est_writer=csv.writer(est_file,lineterminator='\r')
	
	if output_config['path_size']:
		path_size_alias=['path_size']
	else:
		path_size_alias=[]
	
	est_writer.writerow(['occ','alt','trip_id','chosen']+output_config['aliases']+path_size_alias+['overlap'])
	
	sans_chosen=copy.deepcopy(path_list_collection)
	for path_list in sans_chosen:
		path_list.pop(0)
	path_size_data=path_size(G,sans_chosen,choice_set_config)
	
	for occ_idx in range(len(path_list_collection)):
		for alt_idx in range(len(path_list_collection[occ_idx])):
			path=path_list_collection[occ_idx][alt_idx]
			values=[]
			for i in range(len(output_config['variables'])):
				if output_config['variables'][i] in master_config['time_dependent_relation']:
					key=get_time_dependent_variable(output_config['variables'][i],trip_times[id_list[occ_idx]],master_config['time_dependent_relation'])
				else:
					key=output_config['variables'][i]
				values.append(str(path_trace(G,path,key,output_config['trace_funs'][i],output_config['final_funs'][i],output_config['weights'][i])))
			if output_config['path_size']:
				if alt_idx==0:
					values.append(0)
				else:
					values.append(path_size_data[occ_idx][alt_idx-1])
			values.append(chosen_overlap[occ_idx][alt_idx])
			est_writer.writerow([str(occ_idx),str(alt_idx),str(id_list[occ_idx]),str(alt_idx==0)]+values)
	
	est_file.close()

import unittest
from bike_model.config.bike_network_config import BikeNetworkConfig
from bike_model.config.bike_output_config import BikeOutputConfig
from route_model.transport_network import TransportNetwork
from route_model.choice_set.link_elimination import link_elimination

class Tests(unittest.TestCase):
	
	def setUp(self):
		
		network_config=BikeNetworkConfig()
	
		self.net=TransportNetwork(network_config)
		self.net.create_node_xy_from_csv(network_config)
		
		self.output_config=BikeOutputConfig()

	def testPathListOutput(self):
		"""path output should work"""
		paths=link_elimination(self.net, 259, 226, self.net.euclid, 'DISTANCE',20)
		create_csv_from_path_list(paths,self.output_config['pathID'],self.output_config['pathLink'])
	
if __name__ == '__main__':
	
	unittest.main()
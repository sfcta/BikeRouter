from route_model.traversal.single_source_dijkstra import single_source_dijkstra
import string

def project_outer_trips(G,matrix,assign_config):
	
	max_inner=assign_config['max_inner']
	importance_conditions=assign_config['outer_importance_conditions']
	
	inner_hash={}
	for i in range(max_inner):
		inner_hash[i+1]=1
	
	end_nodes={}	
	for condit in importance_conditions:
		for i in range(condit[0],condit[1]):
			
			the_target={}
			for j in range(max_inner):
				if matrix[i-1,j]>0 or matrix[j,i-1]>0:
					the_target[j+1]=1
					
			if not the_target:
				continue
			
			dist,paths=single_source_dijkstra(G,i,assign_config['outer_impedance'],target=the_target)

			for j in the_target:
				for k in range(len(paths[j])):
					if G[paths[j][k]][paths[j][k+1]][assign_config['boundary_condition']]:
						break
				node=paths[j][k]
				newdist,newpaths,centroid=single_source_dijkstra(G,node,assign_config['outer_impedance'],target=inner_hash,allow_centroids=True,target_type=1)
				#print string.join([str(i),str(centroid),str(j),str(matrix[i-1,j-1]),str(matrix[j-1,i-1])],'\t')
				matrix[centroid-1,j-1]=matrix[centroid-1,j-1]+matrix[i-1,j-1]
				matrix[j-1,centroid-1]=matrix[j-1,centroid-1]+matrix[j-1,i-1]
			
	matrix=matrix[:max_inner,:max_inner]
	
	return matrix
	
import unittest
from bike_model.config.bike_master_config import BikeMasterConfig
from route_model.transport_network import TransportNetwork
from route_model.input import read_matrix
from route_model.output import create_csv_from_matrix

class Tests(unittest.TestCase):
	
	def setUp(self):
		
		self.master_config=BikeMasterConfig()
		self.net=TransportNetwork(self.master_config.outer_network_config)
		self.matrix=read_matrix(self.master_config.assign_config['matrix_filenames'][0])
		self.master_config.output_config.setup_files()

	def testProjectOuterTrips(self):
		"""projecting outer trips should work"""
		self.matrix=project_outer_trips(self.net,self.matrix,self.master_config.assign_config)
		create_csv_from_matrix(self.matrix,self.master_config)
	
if __name__ == '__main__':
	
	unittest.main()
	


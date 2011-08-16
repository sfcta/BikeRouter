#!/usr/bin/env python

'''Converts trip table to within-sf trips.
'''

import logging, string
from bikeAssign.traversal.single_source_dijkstra import single_source_dijkstra

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

def project_outer_trips(G,matrix,assign_config):
    """
    Converts trip table to within-sf trips.
    """    

    max_inner=assign_config['max_inner'] # e.g. 981
    
    # nothing to do
    if matrix.shape[0] <= max_inner: return matrix
    
    withinsf = matrix[:max_inner,:max_inner]
    logstr = "project_outer_trips: From %d trips (%d within SF) in %s" % (matrix.sum(), withinsf.sum(), str(matrix.shape))
    
    inner_hash={}
    for i in range(max_inner):
        inner_hash[i+1]=1
    
    end_nodes={}    
    unconnected={}
    
    # zones with non-negligible trips to SF, 
    # e.g. [(982,1348),(2403,2455)]
    for condit in assign_config['outer_importance_conditions']: 
        for external_taz in range(condit[0],condit[1]):
            
            if external_taz not in G: continue
            
            the_target={}
            for j in range(max_inner): # j+1 is the internal taz
                if matrix[external_taz-1,j]>0 or matrix[j,external_taz-1]>0:
                    the_target[j+1]=1
                    
            if not the_target:
                continue
            
            dist,paths=single_source_dijkstra(G,external_taz,assign_config['outer_impedance'],target=the_target)

            for internal_taz in the_target:
                if internal_taz not in paths:
                    if internal_taz not in unconnected: 
                        print "project_outer_trips: Node %d not in paths although it's in targets." % (internal_taz)
                        unconnected[internal_taz]=1
                    continue
                
                for k in range(len(paths[internal_taz])):
                    if G[paths[internal_taz][k]][paths[internal_taz][k+1]][assign_config['boundary_condition']]:
                        break
                node=paths[internal_taz][k]
                newdist,newpaths,centroid=single_source_dijkstra(G,node,assign_config['outer_impedance'],
                                                                 target=inner_hash,
                                                                 allow_centroids=True,target_type=1)
                #print string.join([str(external_taz),str(centroid),str(internal_taz),str(matrix[external_taz-1,internal_taz-1]),str(matrix[internal_taz-1,external_taz-1])],'\t')
                matrix[centroid-1,internal_taz-1]=matrix[centroid-1,internal_taz-1]+matrix[external_taz-1,internal_taz-1]
                matrix[internal_taz-1,centroid-1]=matrix[internal_taz-1,centroid-1]+matrix[internal_taz-1,external_taz-1]
            
    matrix=matrix[:max_inner,:max_inner]

    logging.info("%s to %d trips in %s" % (logstr, matrix.sum(), str(matrix.shape)))
    
    return matrix
    
import unittest
# from bike_model.config.bike_master_config import BikeMasterConfig
from bikeAssign.transport_network import TransportNetwork
from bikeAssign.input import read_matrix
from bikeAssign.output import create_csv_from_matrix

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
    


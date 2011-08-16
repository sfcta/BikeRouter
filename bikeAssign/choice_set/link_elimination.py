#!/usr/bin/env python

'''needs doc
'''

import random
from bikeAssign.traversal.a_star import a_star

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

def le_generate(G,chosen,choice_set_config):
	
	master_set=link_elimination(G,chosen[0],chosen[-1],G.euclid,G.config['dist_var'],choice_set_config['master_size'])
	chosen_overlap=calc_chosen_overlap(G,chosen,master_set,choice_set_config)
	sample_set=random.sample(master_set,choice_set_config['consider_size'])
	result_set=[chosen]
	chosen_seen=False
	for path in sample_set:
		if chosen_seen==False:
			if path==result_set[0]:
				chosen_seen=True
				if not choice_set_config['allow_duplicates_of_chosen_route']:
					continue
		result_set.append(path)
	if chosen_seen==False and not choice_set_config['allow_duplicates_of_chosen_route']:
		result_set.pop()
	return (result_set,chosen_overlap)

def link_elimination(G,start,goal,heuristic,varname,size):
	"""generates a route choice set from start to goal using breadth first seach of the link elimination tree"""
	
	queue = [[]] #list of lists of edges to be eliminated in subgraphs
	paths = [] #list of shortest paths
	seen = [] #list of lists of edges already eliminated at current depth
	depths = []

	depth=0

	while queue and len(paths)<size:
		
		if len(queue[0])>depth:
			random.shuffle(queue)
			depth=depth+1
			seen=[]
			
		curbunch = queue.pop(0)
		
		for seenbunch in seen:
			if curbunch==seenbunch:
				break
		else:
			shortest = a_star(G,start,goal,heuristic,varname,curbunch)
			if shortest is None:
				continue
			if shortest not in paths:
				paths.append(shortest)
				depths.append([len(curbunch)])
			for i in range(len(shortest)-1):
				queue.append(sorted(curbunch+[(shortest[i],shortest[i+1])]))
			seen.append(curbunch)
			
	return paths

def calc_chosen_overlap(G,chosen,master_set,choice_set_config):
	config=choice_set_config
	filtered=[]
	L=0
	alt=0
	chosen_hash={}
	chosen_length={}
	chosen_overlap=0.0
	for cur_path in ([chosen]+master_set):
		cur_hash={}
		cur_length=0.0
		if G.orig_network is None:
			R=len(cur_path)-1
		else:
			R=len(cur_path)-2
		for i in range(R):
			cur_hash[(cur_path[i],cur_path[i+1])]=1
			if type(cur_path[i])==type(0) and type(cur_path[i+1])==type((1,2)):
				cur_length=cur_length+G.orig_network[cur_path[i+1][0]][cur_path[i+1][1]][config['overlap_var']]
			else:
				cur_length=cur_length+G[cur_path[i]][cur_path[i+1]][config['overlap_var']]
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
						intersect_length=intersect_length+G.orig_network[e[1][0]][e[1][1]][config['overlap_var']]
					else:
						intersect_length=intersect_length+G[e[0]][e[1]][config['overlap_var']]
			chosen_overlap=max(chosen_overlap,intersect_length/chosen_length)
		alt=alt+1
	
	return chosen_overlap

import unittest
# from bike_model.config.bike_network_config import BikeNetworkConfig
from bikeAssign.transport_network import TransportNetwork

class Tests(unittest.TestCase):
	
	def setUp(self):
		
		network_config=BikeNetworkConfig()
	
		self.net=TransportNetwork(network_config)
		self.net.create_node_xy_from_csv(network_config)

	def testLinkEliminationNoPathsEqual(self):
		"""link elimination should return no paths that are the same"""
		paths=link_elimination(self.net, 259, 226, self.net.euclid, 'DISTANCE',20)
		for i in range(len(paths)):
			for j in range(i-1):
				self.assertNotEqual(paths[i],paths[j])
				
	def testLinkEliminationNumPaths(self):
		"""link elimination should return the number of paths requested"""
		paths=link_elimination(self.net, 259, 226, self.net.euclid, 'DISTANCE',20)
		self.assertEqual(len(paths),20)
		
	def testLinkEliminationStartGoal(self):
		"""link elimination should return paths that all go from start to goal"""
		paths=link_elimination(self.net, 259, 226, self.net.euclid, 'DISTANCE',20)
		for i in range(len(paths)):
			self.assertEqual(paths[i][0],259)
			self.assertEqual(paths[i][-1],226)
	
	def testLinkEliminationNoCentroid(self):
		"""link elimination should return paths that don't use intermediate centroids"""
		paths=link_elimination(self.net, 259, 226, self.net.euclid, 'DISTANCE',20)
		if self.net.config['max_centroid'] is None:
			raise Exception('max_centroid is None, test is trivial')
		for i in range(len(paths)):
			for j in range(1,len(paths[i])-1):
				self.assertFalse(paths[i][j]<=self.net.config['max_centroid'])

if __name__ == '__main__':
	
	unittest.main()
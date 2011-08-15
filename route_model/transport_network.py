from networkx.classes.digraph import DiGraph
import os, csv
from math import sqrt, acos, pi
from numpy import *

class TransportNetwork(DiGraph):
	"""network data structure"""

	def __init__(self,config=None):
		"""fill out the link data from the csv file"""
		
		DiGraph.__init__(self)
		
		self.config=config
		
		if config is not None:

			infile=open(config['link_file'])
			reader=csv.reader(infile)

			data=[]
			names=[]
			
			for row in reader:
				if row[0]=='A': names=row
				else: data.append(row)

			M=len(data)
			N=len(names)
			
			if 'perform_transformation' in config:
				
				if config['perform_transformation']:
				
					
					#create wrong way links
					if config['create_ww_links']:
						names.append(config['ww_exist_alias'][1])
						for i in range(M):
							if int(	data[i][names.index(config['ww_exist_alias'][0])]	)==1:
								new_row=data[i]+[1]
								if len(new_row)<len(names):
									print 'A'
									raise Exception
								for var in config['ww_change']:
									idx=names.index(var)
									stmt="new_row[idx]=float(new_row[idx])"+config['ww_change'][var][0]+"config['ww_change'][var][1]"
									###print names
									###print data[i]
									exec(stmt)
								if len(new_row)<len(names):
									print 'B'
									raise Exception
								data.append(new_row)
						
							data[i].append(0)
				
					M=len(data)
					N=len(names)
					
				
					#transform variables
					for var in config['variable_transforms']:
						names.append(var)
						for i in range(M):
							if type(config['variable_transforms'][var][1])==type({}):
								stmt="data[i].append(config['variable_transforms'][var][1]["+config['variable_transforms'][var][2]+"(data[i][names.index(config['variable_transforms'][var][0])])])"
								exec(stmt)
							else:
								if type(config['variable_transforms'][var][1])==type((1,2)):
									stmt="data[i].append("+config['variable_transforms'][var][1][0]+"("+config['variable_transforms'][var][2]+"(data[i][names.index(config['variable_transforms'][var][0])]),config['variable_transforms'][var][1][1]))"
									exec(stmt)
								else:
									print 'D'
									raise Exception
								
			M=len(data)
			N=len(names)
			
			if 'relevant_variables' in config:
				to_keep=[]
				for var in config['relevant_variables']:
					to_keep.append(names.index(var))
			else:
				to_keep=range(2,N)
			
			for i in range(M):
				edge_data={}
				for j in to_keep:
					try:
						edge_data[names[j]]=float(data[i][j])
					except IndexError:
						print names
						print j
						print data[i]
						print i
						print to_keep
						print len(names)
						print len(data[i])
						raise Exception
				self.add_edge(int(data[i][0]),int(data[i][1]),edge_data)
			
			infile.close()
			
			if 'node_file' in config:
				self.create_node_xy_from_csv(config)
				
		self.orig_network=None
	
	def create_node_xy_from_csv(self,config):
		"""fill out the geographical node locations from the csv file"""
		
		infile=open(config['node_file'])
		reader=csv.reader(infile)

		self.node_xy={}

		for row in reader:
			if row[0]=='N': continue
			else: self.node_xy[int(row[0])]=(float(row[1]),float(row[2]))
				
		infile.close()
	
	def select_edges_where(self,varname,operator,value_or_iterable,data=True):
		"""allowed operators: '<', '==', '>', '<=', '>=', '!=', 'in', 'not in'
		list of values allowed only if operator is 'in' or 'not in'"""
		
		ebunch=[]
		
		try:
			iter(value_or_iterable)
			if operator not in ['in', 'not in']:
				raise TransportNetworkError('operator not compatible with iterable')
		except TypeError: pass
		
		if data: substr='e'
		else: substr='(e[0],e[1])'
		
		if varname=='A':
			stmt='if e[0] ' + operator + ' ' + str(value_or_iterable) + ':\n   ebunch.append(' + substr + ')'  
		elif varname=='B':
			stmt='if e[1] ' + operator + ' ' + str(value_or_iterable) + ':\n   ebunch.append(' + substr + ')'
		else:
			stmt='if e[2][varname] ' + operator + ' ' + str(value_or_iterable) + ':\n   ebunch.append(' + substr + ')'
		
		for e in self.edges(data=True):
			exec(stmt)
				
		return ebunch
		
	def euclid(self,n1,n2):
		"""euclidean distance heuristic with rescaling from node distances to link distances"""
		
		return self.config['dist_scl']*sqrt(((self.node_xy[n1][0]-self.node_xy[n2][0]))**2+((self.node_xy[n1][1]-self.node_xy[n2][1]))**2)

	def node_dot_product(self,n11,n12,n21,n22):
		
		return (self.node_xy[n12][0]-self.node_xy[n11][0])*(self.node_xy[n22][0]-self.node_xy[n21][0])+(self.node_xy[n12][1]-self.node_xy[n11][1])*(self.node_xy[n22][1]-self.node_xy[n21][1])

	def node_cross_product_z(self,n11,n12,n21,n22):
		
		vec_1 = (self.node_xy[n12][0]-self.node_xy[n11][0],self.node_xy[n12][1]-self.node_xy[n11][1])
		vec_2 = (self.node_xy[n22][0]-self.node_xy[n21][0],self.node_xy[n22][1]-self.node_xy[n21][1])
		
		return vec_1[0]*vec_2[1]-vec_1[1]*vec_2[0]
	
	def edge_dot_product(self,e1,e2):
		
		return self.node_dot_product(e1[0],e1[1],e2[0],e2[1])
		
	def edge_cross_product_z(self,e1,e2):
		
		return self.node_cross_product_z(e1[0],e1[1],e2[0],e2[1])
		
	def edge_length(self,e):
		
		return sqrt(self.edge_dot_product(e,e))
		
	def edge_angle(self,e1,e2):
		
		arg=self.edge_dot_product(e1,e2)/(self.edge_length(e1)*self.edge_length(e2))
		arg=min(arg,1)
		arg=max(arg,-1)
		ang=acos(arg)
		return ang
		
	def is_turn(self,e1,e2):
		
		if e1[1]!=e2[0]:
			return False
			
		if e1[0]<=self.config['max_centroid'] or e1[1]<=self.config['max_centroid'] or e2[0]<=self.config['max_centroid']:
			return False
			
		examine_angle=self.edge_angle(e1,e2)
		
		min_angle=examine_angle
		for nbr in self[e1[1]]:
			cur_angle=self.edge_angle(e1,(e1[1],nbr))
			min_angle=min(min_angle,cur_angle)
			
		return (min_angle<examine_angle/3 and examine_angle>pi/6)
		
	def turn_dir(self,e1,e2):
		
		if not self.is_turn(e1,e2):
			return False
		if self.edge_angle(e1,e2)>5*pi/6:
			return 'U'
		else:
			if self.edge_cross_product_z(e1,e2)>0:
				return 'L'
			else:
				return 'R'
				
	def make_centroid_gateways(self):
		
		if self.orig_network is None:
			raise TransportNetworkError('cannot make gateways for non-dual network')
		else:
			for centroid in range(1,self.config['max_centroid']+1):
				if centroid in self.orig_network:
					for neighbor in self.orig_network.successors_iter(centroid):
						self.add_edge(centroid,(centroid,neighbor),dict(self.orig_network[centroid][neighbor],**{'TURN':0,'R_TURN':0,'L_TURN':0}))
					for neighbor in self.orig_network.predecessors_iter(centroid):
						new_data=dict(self.orig_network[neighbor][centroid],**{'TURN':0,'R_TURN':0,'L_TURN':0})
						for key in new_data:
							new_data[key]=0
						self.add_edge((neighbor,centroid),centroid,new_data)
					
	def remove_centroid_gateways(self):
		
		if self.orig_network is None:
			raise TransportNetworkError('cannot remove gateways for non-dual network')
		else:
			for centroid in range(1,self.config['max_centroid']+1):
				if centroid in self.orig_network:
					for centroid in range(1,self.config['max_centroid']+1):
						for neighbor in self.orig_network.successors_iter(centroid):
							self.remove_edge((centroid,neighbor),neighbor)
						for neighbor in self.orig_network.predecessors_iter(centroid):
							self.remove_edge((neighbor,centroid),centroid)

def create_pseudo_dual(G):
	
	H=TransportNetwork()
	H.config=G.config
	
	for e1 in G.edges_iter(data=True):
		for e2 in G.edges([e1[1]],data=True):
			dual_data=e2[2]
			dual_data['TURN']=0
			dual_data['L_TURN']=0
			dual_data['R_TURN']=0
			dual_data['U_TURN']=0
			the_turn=G.turn_dir(e1,e2)
			if the_turn:
				dual_data['TURN']=1
				if the_turn=='L':
					dual_data['L_TURN']=1
				if the_turn=='R':
					dual_data['R_TURN']=1
				if the_turn=='U':
					dual_data['U_TURN']=1
			H.add_edge((e1[0],e1[1]),(e2[0],e2[1]),attr_dict=dual_data)
			
			
	H.orig_network=G.copy()
						
	return H

class TransportNetworkError(Exception):
	pass
	
import unittest
from route_model.config.network_config import NetworkConfig

class Tests(unittest.TestCase):
	
	def setUp(self):
		
		network_config=NetworkConfig()
	
		self.net=TransportNetwork(network_config)
		self.net.create_node_xy_from_csv(network_config)
	
	def testSelectEdgesWhereKnownValues(self):
		"""select_edges_where should give known result with known input"""
		x=sorted(self.net.select_edges_where('DISTANCE','==',1,data=False))
		y=sorted([(1,2),(2,4)])
		self.assertEqual(x,y)
		
	def testSelectEdgesWhereBadOperator(self):
		"""select_edges_where should fail with bad operator"""
		self.assertRaises(Exception,self.net.select_edges_where,'DISTANCE','=',1)

	def testSelectEdgesWhereIncompatible(self):
		"""select_edges_where should fail with iterator and incompatible operator"""
		self.assertRaises(TransportNetworkError,self.net.select_edges_where,'DISTANCE','==',[1,2])

	def testEuclidEqualsDistance(self):
		"""euclid should give known result with known input"""
		x=self.net.euclid(3,4)
		y=self.net[3][4]['DISTANCE']
		self.assertAlmostEqual(x,y)
		
	def testEdgeAngleKnownValues(self):
		"""edge_angle should give known result with known input"""
		x=self.net.edge_angle((1,3),(3,4))
		self.assertAlmostEqual(x,3*pi/4)
		
if __name__=='__main__':
	
	unittest.main()

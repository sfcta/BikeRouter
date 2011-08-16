#!/usr/bin/env python

'''needs doc
'''

import random
import numpy.random as nr
from bikeAssign.choice_set.link_randomizer import LinkRandomizer

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

class BetaUnifRandomizer(LinkRandomizer):
	
	def __init__(self,G,variables,no_randomize,b,s,scl):			
			
		LinkRandomizer.__init__(self)
		
		self['variables']=variables
		self['no_randomize']=no_randomize

		self.set_scl(scl)
		self.set_fam(nr.beta,nr.uniform)
		self.set_par([1,b],[1-s,1+s])
		
		self.get_link_distribution(G)
		
		self.get_fam_means()
		self.update_denoms()
		
	def get_fam_means(self):
		
		self['zero']['mean']=self['zero']['par'][0]/(self['zero']['par'][0]+self['zero']['par'][1])
		self['pos']['mean']=(self['pos']['par'][0]+self['pos']['par'][1])/2

import unittest
# from bike_model.config.bike_network_config import BikeNetworkConfig
from bikeAssign.transport_network import TransportNetwork

class Tests(unittest.TestCase):

	def setUp(self):

		bike_network_config=BikeNetworkConfig()
		self.bikenet=TransportNetwork(bike_network_config)
		self.bikenet.create_node_xy_from_csv(bike_network_config)

	def testBetaUnifRandomizer(self):
		"""BetaUnifRandomizer should work"""
		bur=BetaUnifRandomizer(self.bikenet,['DISTANCE','B0'],2,.5,.25)
		for key in ['DISTANCE','B0']:
			for b,data in self.bikenet[25908].iteritems():
				print key, data[key], bur.generate_value(self.bikenet,25908,b,key)
				
if __name__ == '__main__':
	
	unittest.main()
		
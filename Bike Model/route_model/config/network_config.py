import os
from UserDict import UserDict

class NetworkConfig(UserDict):
	"""store network configuration data"""
	
	def __init__(self, changes={}):
		UserDict.__init__(self)
		self['data_dir']=r"X:\Projects\BikeModel\data\route_model\input\network\test"
		self['link_file']=os.path.join(self['data_dir'],'links.csv')
		self['node_file']=os.path.join(self['data_dir'],'nodes.csv')
		self['dist_var']='DISTANCE'
		self['dist_scl']=1 #rescales with node distance x dist_scl= link distance
		self['max_centroid']=None

		for key in changes:
			self[key]=changes[key]
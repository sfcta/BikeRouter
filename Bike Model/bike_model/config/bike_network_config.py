import os
from route_model.config.network_config import NetworkConfig

class BikeNetworkConfig(NetworkConfig):
	"""store network configuration data"""
	
	def __init__(self, changes={}):
		NetworkConfig.__init__(self)
		self['data_dir']=r"X:\Projects\BikeModel\data\bike_model\input\network\2010_04_10"
		self['link_file']=os.path.join(self['data_dir'],'links.csv')
		self['node_file']=os.path.join(self['data_dir'],'nodes.csv')
		self['dist_var']='DISTANCE'
		self['dist_scl']=1/5280 #rescales with node distance x dist_scl= link distance
		self['max_centroid']=2454
		self['exclude_group']={'FT':('in',[1,2,101,102])}
		
		self['use_dual']=True
		
		for key in changes:
			self[key]=changes[key]

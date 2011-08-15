import os
from route_model.config.master_config import MasterConfig

class BikeMasterConfig(MasterConfig):
	"""compile configuration data"""
	
	def __init__(self, changes={}):
		MasterConfig.__init__(self,changes)
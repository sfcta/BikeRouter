import os
from route_model.config.master_config import MasterConfig
from bike_model.config.bike_choice_set_config import BikeChoiceSetConfig

class LinkEliminationMasterConfig(MasterConfig):
	"""compile configuration data"""
	
	def __init__(self, changes={}):
		MasterConfig.__init__(self,changes)
		
		self.choice_set_config=BikeChoiceSetConfig(method='link_elimination')
		self.network_config['use_dual']=False
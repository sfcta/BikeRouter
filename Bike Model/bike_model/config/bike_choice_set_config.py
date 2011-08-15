from route_model.config.choice_set_config import ChoiceSetConfig

class BikeChoiceSetConfig(ChoiceSetConfig):
	"""store choice set generation configuration data"""
	
	def __init__(self,changes={},method='doubly_stochastic'):
		
		changes['verbose']=True
		
		ChoiceSetConfig.__init__(self,changes,method)
import os
from UserDict import UserDict
from bike_model.config.bike_network_config_direct_from_cube import BikeNetworkConfigDirectFromCube
from bike_model.config.outer_network_config import OuterNetworkConfig
from bike_model.config.bike_output_config import BikeOutputConfig
from bike_model.config.bike_choice_set_config import BikeChoiceSetConfig
from route_model.config.assign_config import AssignConfig

class MasterConfig(UserDict):
	"""compile configuration data"""
	
	def __init__(self, changes={}):
		UserDict.__init__(self)
		
		self.network_config=BikeNetworkConfigDirectFromCube()
		self.outer_network_config=OuterNetworkConfig()
		self.output_config=BikeOutputConfig()
		self.choice_set_config=BikeChoiceSetConfig()
		self.assign_config=AssignConfig()
		
		#location of travel data in matsim format
		self['travel_dir']=r"X:\Projects\BikeModel\data\bike_model\input\travel\2010_04_18"
		
		#directory with trip start times in hours on 24 hr clock
		self['time_file']=r"X:\Projects\BikeModel\data\bike_model\input\context\2010_04_18\time.csv"
		
		#to holdback a sample of observations from estimation to use for validation
		self['use_holdback_sample']=True
		self['holdback_rate']=0.10
		self['holdback_from_file']=True
		self['holdback_file']=r"X:\Projects\BikeModel\data\bike_model\input\holdback\Holdback.csv"
		
		self['n_processes']=4
		
		"""deprecated"""
		#rules to lookup time dependent variables in network data { variable in choice_set_config : [ ( (time lower bound, time upper bound) , variable to lookup), ... ,('else', variable to lookup if time outside preceeding bounds) ]}
		#else condition must be last for each rule
		self['time_dependent_relation']={'V':[((3,6),'V_EA'),((6,9),'V_AM'),((9,15.5),'V_MD'),((15.5,18.5),'V_PM'),('else','V_EV')]}
		
		#this gives the location of travel data with chosen routes that are hard to reproduce, used in route_model.evaluate_parameters
		self['imperfect_file']=r"X:\Projects\BikeModel\data\bike_model\input\optim\imperfect.csv"
		
		for key in changes:
			self[key]=changes[key]
import os, time
from route_model.config.output_config import OutputConfig

class BikeOutputConfig(OutputConfig):
	"""store output configuration data"""
	
	def __init__(self, changes={}):
		OutputConfig.__init__(self,{'output_dir':r"X:\Projects\BikeModel\data\bike_model\output"})
		
		for key in changes:
			self[key]=changes[key]
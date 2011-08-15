import os
from UserDict import UserDict
from math import exp
from numpy import *

class AssignConfig(UserDict):
	"""compile configuration data"""
	
	def __init__(self, changes={}):
		UserDict.__init__(self)
		
		"""how to project outer trips to the county line"""
		self['max_inner']=981	#maximum zone id for SF county
		self['outer_importance_conditions']=[(982,1348),(2403,2455)]	#zones with non-negligible trips to SF
		self['boundary_condition']='MTYPE'	#network variable that indicates links which are inside SF
		self['outer_impedance']="DISTANCE"	#netowrk variable to minimize when projecting trips to county line
		
		"""trip matrices to assign"""
		self['matrix_filenames']=[r"X:\Projects\BikeModel\data\bike_model\input\matrix\am.csv",
							r"X:\Projects\BikeModel\data\bike_model\input\matrix\md.csv",
							#r"X:\Projects\BikeModel\data\bike_model\input\matrix\pm.csv",
							#r"X:\Projects\BikeModel\data\bike_model\input\matrix\ev.csv",
							#r"X:\Projects\BikeModel\data\bike_model\input\matrix\ea.csv"
							]
		self['load_names']=['BIKE_AM','BIKE_PM']#'BIKE_MD','BIKE_EV','BIKE_EA'
		
		"""override bound_file from choice_set_config"""
		self['bound_file']=r'X:\Projects\BikeModel\data\bike_model\input\bound\BoundPredict.csv'

		"""use x times as many random seeds as needed for each source"""
		self['inverted_multiple']=2

		"""path storage"""
		self['pickle_path']='C:/pickle_path'	#directory to store path files
		self['delete_paths']=False	#delete the paths after assignment is complete?
		self['load_paths_from_files']=False	#use already generated paths rather than starting anew?
		
		"""how to trace variables for utility function"""
		self['variables']=['DISTANCE',
						'B1',
						'B2',
						'B3',
						'TPER_RISE',
						'WRONG_WAY',
						'TURN']
		self['aliases']=['DISTANCE',
						'BIKE_PCT_1',
						'BIKE_PCT_2',
						'BIKE_PCT_3',
						'AVG_RISE',
						'WRONG_WAY',
						'TURNS_P_MI']
		self['weights']=[None,
						'DISTANCE',
						'DISTANCE',
						'DISTANCE',
						'DISTANCE',
						'DISTANCE',
						None]
		self['trace_funs']=['sum',
						'avg',
						'avg',
						'avg',
						'avg',
						'avg',
						'sum']
		self['final_funs']=[None,None,None,None,None,None,None]
		self['path_size']=True
		self['path_size_log']=True
		self['path_size_alias']='lnpathsize'
		self['divisors']={'TURNS_P_MI':'DISTANCE'}	# calculate this alias by dividing by this variable
		
		"""fixed coefficients"""
		self['fixed_coefficients']=['DISTANCE','TURNS_P_MI','WRONG_WAY','BIKE_PCT_1','BIKE_PCT_2','BIKE_PCT_3','AVG_RISE','lnpathsize']
		self['alpha']=[-1.05,-0.21,-13.30,1.89,2.15,0.35,-154.0,1.0]
		
		"""random coefficients"""
		self['use_random_coefficients']=False
		self['random_coefficients']=[]#['BIKE_PCT_1','BIKE_PCT_2','BIKE_PCT_3','AVG_RISE']
		self['random_transformations']=[]#[idenfun,idenfun,idenfun,idenfun]
		self['latent_mu']=[]#[1.82,2.49,0.76,-2.22]
		self['latent_sigma']=array([])
		"""array( [	[24.95,	0.,	6.58,	0.	],
								[0.,		5.45,	2.91,	0.	],
								[0.,		0.,	4.19,	0.	],
								[0.,		0.,	0.,	3.85	]	] )"""
		self['mixing_granularity']=0.2 # number of trips to simulate as an individual
		
		"""for debugging code"""
		self['test_small_matrix']=True
	
		for key in changes:
			self[key]=changes[key]
			
def idenfun(x):
	return x
	
def negexp(x):
	return -exp(x)
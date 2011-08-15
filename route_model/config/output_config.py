import os, time, string
from UserDict import UserDict

class OutputConfig(UserDict):
	"""store output configuration data"""
	
	def __init__(self,changes={}):
		UserDict.__init__(self)
		self['output_dir']=r"X:\Projects\BikeModel\data\route_model\output"
		self['filename_dict']={'pathID':'PathID.csv',
							'pathLink':'PathLink.csv',
							'estimation_data':'EstimationData.csv',
							'bound_data':'Bound.csv',
							'overlap_data':'Overlap.csv',
							'matrix_data':'Matrix.csv',
							'assign_data':'Assign.csv',
							'holdback_file':'Holdback.csv'}
		self['output_type']=['estimation','bound','geographic','overlap','assign','holdback_sample']
		
		#estimation variable configuration
		self['variables']=['DISTANCE',
						'B1',
						'B2',
						'B3',
						'TPER_RISE',
						'CRIME',
						'SPEED',
						'WRONG_WAY',
						'V_TOT',
						'TURN',
						'WATERFRONT',
						'LANE_OP']
		self['aliases']=['DISTANCE',
						'BIKE_PCT_1',
						'BIKE_PCT_2',
						'BIKE_PCT_3',
						'AVG_RISE',
						'AVG_CRIME',
						'AVG_SPEED',
						'WRONG_WAY',
						'AVG_VOL',
						'TURNS',
						'WF_PCT',
						'AVG_LANES']
		self['weights']=[None,
						'DISTANCE',
						'DISTANCE',
						'DISTANCE',
						'DISTANCE',
						'DISTANCE',
						'DISTANCE',
						'DISTANCE',
						'DISTANCE',
						None,
						'DISTANCE',
						'DISTANCE']
		self['trace_funs']=['sum',
						'avg',
						'avg',
						'avg',
						'avg',
						'avg',
						'avg',
						'avg',
						'avg',
						'sum',
						'avg',
						'avg']
		self['final_funs']=[None,None,None,None,None,None,None,None,None,None,None,None]
		self['path_size']=True
		
		for key in changes:
			self[key]=changes[key]
		
		self.set_time_dir()
		
	def set_time_dir(self):
		start_time=time.localtime()
		self['time']=''
		for i in range(6):
			self['time']=self['time']+string.zfill(start_time[i],2)
			if i<5:
				self['time']=self['time']+'_'
		os.mkdir(os.path.join(self['output_dir'],self['time']))
				
	def setup_files(self):
		for key in self['filename_dict']:
			self[key]=os.path.join(self['output_dir'],self['time'],self['filename_dict'][key])
import os
from route_model.config.network_config import NetworkConfig

class BikeNetworkConfigDirectFromCube(NetworkConfig):
	"""store network configuration data"""
	
	def __init__(self, changes={}):
		NetworkConfig.__init__(self)
		self['data_dir']=r"X:\Projects\BikeModel\data\bike_model\input\network\2010_06_08"
		self['link_file']=os.path.join(self['data_dir'],'links.csv')
		self['node_file']=os.path.join(self['data_dir'],'nodes.csv')
		self['dist_var']='DISTANCE'
		self['dist_scl']=1/5280 #rescales with node distance x dist_scl= link distance
		self['max_centroid']=2454
		self['exclude_group']={'FT':('in',[1,2,101,102]),'MTYPE_NUM':('==',0)}
		
		self['use_dual']=True
		
		self['perform_transformation']=True
		self['ww_exist_alias']=('ONEWAY','WRONG_WAY')
		self['ww_change']={'FT':('+',100),'BIKE_CLASS':('*',0),'PER_RISE':('*',-1)}
		self['variable_transforms']={	'MTYPE_NUM'	:('MTYPE',		{'SF':1,'MTC':0}	,	""		),
								'B0'			:('BIKE_CLASS',	{0:1,1:0,2:0,3:0}		,	"int"	),
								'B1'			:('BIKE_CLASS',	{0:0,1:1,2:0,3:0}		,	"int"	),
								'B2'			:('BIKE_CLASS',	{0:0,1:0,2:1,3:0}		,	"int"	),
								'B3'			:('BIKE_CLASS',	{0:0,1:0,2:0,3:1}		,	"int"	),
								'BNE1'		:('BIKE_CLASS',	{0:1,1:0,2:1,3:1}		,	"int"	),
								'BNE2'		:('BIKE_CLASS',	{0:1,1:1,2:0,3:1}		,	"int"	),
								'BNE3'		:('BIKE_CLASS',	{0:1,1:1,2:1,3:0}		,	"int"	),
								'TPER_RISE'	:('PER_RISE',	('max',0)			,	"float"	)
							}
		self['relevant_variables']=['DISTANCE','FT','MTYPE_NUM','TPER_RISE','WRONG_WAY','B0','B1','B2','B3','BNE1','BNE2','BNE3']					
							
		
		

		for key in changes:
			self[key]=changes[key]

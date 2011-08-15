import os
from UserDict import UserDict
import random
import route_model.misc as rm_misc
from route_model.choice_set.beta_unif_randomizer import BetaUnifRandomizer
from math import sqrt

class ChoiceSetConfig(UserDict):
	"""store choice set generation configuration data"""
	
	def __init__(self,changes={},method='doubly_stochastic'):
		UserDict.__init__(self)
		
		if method=='link_elimination':
			self['method']='link_elimination'
			self['master_size']=96
			self['consider_size']=96
			self['overlap_var']='DISTANCE'
			self['only_bound']=False
			self['inverted']=False
			self['allow_duplicates_of_chosen_route']=True
			
		else:
			self['method']='doubly_stochastic'
			
			"""filtering parameters"""
			self['overlap_threshold']=0.9	# filter out routes that have an overlap above this
			self['overlap_var']='DISTANCE'	# network variable for calculating overlap
			
			"""prior coefficient distribution parameters"""
			self['ext_bound']=True			# use same distribution for each observation (False is deprecated)
			self['only_bound']=False		# in prepare_estimation.py, only extract prior distribution rather than continuing to generate choice sets?
			self['bound_from_file']=True 	# use distribution from file rather than extracting?
			self['bound_file']=r'X:\Projects\BikeModel\data\bike_model\input\bound\BoundPredict.csv' #file to use
			self['bound_file_override']=True # override variable configuration in this choice_set_config if using file?
			self['bounding_box_sample_size']=500 # max number of observations to sample
			self['tolerance']=0.01 			# percentage threshold to stop binary search when extracting prior distribution
			self['log_prior']=True 			# use log-uniform prior? (False means uniform prior)
			
			"""variable configuration"""
			self['variables']=['DISTANCE','BNE1','BNE2','BNE3','WRONG_WAY','TPER_RISE','TURN']	#network variables to use in choice set generation
			self['ref']='DISTANCE'		#reference variable (coef fixed to 1)
			self['ranges']={'BNE1':[0.0000001,1000.0],'BNE2':[0.0000001,1000.0],'BNE3':[0.0000001,1000.0],'TPER_RISE':[0.00001,100000.0],'WRONG_WAY':[0.0000001,1000.0],'TURN':[0.0000001,1000.0]}	#large initial boundary intervals
			self['weights']={'BNE1':'DISTANCE','BNE2':'DISTANCE','BNE3':'DISTANCE','TPER_RISE':'DISTANCE','WRONG_WAY':'DISTANCE'}		#to multiply each link attribute value by
			self['median_compare']=['TURN']	#extract these coefficients with others at their medians (must appear last in self['variables'])
			self['randomize_compare']=[] #extract these coefficients with link randomization (must appear last in self['variables'])
			
			"""generate noisy output?"""
			self['verbose']=True
			
			"""speed up by randomizing whole network in outer loop and performing searches in inner loop using only comparisons/additions"""
			self['inverted']=True		# should we?
			self['inverted_N_attr']=4	# when link attributes were randomized individually, this controlled the number of link randomizations, now just set it to the number of processors
			self['inverted_N_param']=5	# when link attributes were randomized individually, this controlled the number of parameters to draw per link randomization, now just set it to the number of parameters desired divided by the number of processors (e.g. w/; N_attr=4 processors x N_param=5 == 20 random parameters)
			self['inverted_nested']=False	# when link attributes were randomized individually, True would nest the attribute and parameter randomization loops, now just leave set to False
			
			"""link randomization parameters"""
			self['randomize_after']=True	# apply link randomization after generalized cost is calcluated rather than to attributes individually?  Leave set to True.
			self['randomize_after_dev']=0.4	# link randomization scale parameter
			self['randomize_after_iters']=3	# number of link randomizations per coefficient (e.g. 20 random parameters x 3 randomize_after_iters == 60 max choice set size)

			"""refrain from filtering out routes that overlap too much with chosen route (used to analyze choice set quality)"""
			self['allow_duplicates_of_chosen_route']=False
		
			"""deprecated"""
			#parameters used to randomize link attributes individually
			self['randomizer_fun']=BetaUnifRandomizer
			beta_scl=0.2
			unif_dev=0.4
			self['randomizer_args']=(2,unif_dev,beta_scl)
			self['no_randomize']=['WRONG_WAY','TURN']
			
			#number of generalized cost coefficients to draw if not using inverted loops
			self['ds_num_draws']=32
			
			#link randomizer optimization parameters
			self['optim_sample_size']=200
			self['optim_kappa_vals']=[0.2,0.25]
			self['optim_sigma_vals']=[0.4,0.5]
		
		for key in changes:
			self[key]=changes[key]
			
	def get_link_randomizer(self,G,master_config):
		"""deprecated"""
		
		true_variable_list=list(self['variables'])
		if master_config['time_dependent_relation'] is not None:
			for var in master_config['time_dependent_relation']:
				if var in true_variable_list:
					for rule in master_config['time_dependent_relation'][var]:
						true_variable_list.append(rule[1])
					true_variable_list.remove(var)
		link_randomizer=self['randomizer_fun'](G,true_variable_list,self['no_randomize'],*self['randomizer_args'])
		
		return link_randomizer
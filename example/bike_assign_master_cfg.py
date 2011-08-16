#!/usr/bin/env python

'''master configuration file
'''

import os, time, string, random, multiprocessing
from UserDict import UserDict
from math import sqrt, exp
from numpy import *
import bikeAssign.misc as rm_misc
from bikeAssign.choice_set.beta_unif_randomizer import BetaUnifRandomizer

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

class BikeAssignMasterCfg(UserDict):
    """compile configuration data"""
    
    def __init__(self, changes={}):
        UserDict.__init__(self)
        
        self.network_config=NetworkConfig()
        self.outer_network_config=OuterNetworkConfig()
        self.output_config=OutputConfig()
        self.choice_set_config=ChoiceSetConfig()
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
        
        self['n_processes']=multiprocessing.cpu_count()
        print "Setting n_processes to %d" % (self['n_processes'])
        
        """deprecated"""
        # rules to lookup time dependent variables in network data { variable in choice_set_config
        #  [ ( (time lower bound, time upper bound) , variable to lookup), ... ,
        #      ('else', variable to lookup if time outside preceeding bounds) ]}
        # else condition must be last for each rule
        self['time_dependent_relation']={'V':[((3,6),'V_EA'),((6,9),'V_AM'),((9,15.5),'V_MD'),((15.5,18.5),'V_PM'),('else','V_EV')]}
        
        #this gives the location of travel data with chosen routes that are hard to reproduce, used in route_model.evaluate_parameters
        self['imperfect_file']=r"X:\Projects\BikeModel\data\bike_model\input\optim\imperfect.csv"
        
        for key in changes:
            self[key]=changes[key]
            
class NetworkConfig(UserDict):
    """store network configuration data"""
    
    def __init__(self, changes={}):
        UserDict.__init__(self)
        self['data_dir']=r"bike_model_input"
        self['link_file']=os.path.join(self['data_dir'],'links.csv')
        self['node_file']=os.path.join(self['data_dir'],'nodes.csv')
        self['dist_var']='DISTANCE'
        self['dist_scl']=1/5280 #rescales with node distance x dist_scl= link distance
        self['max_centroid']=2454
        self['exclude_group']={'FT':('in',[1,2,101,102]),'MTYPE_NUM':('==',0)}
        
        self['use_dual']=True
        
        self['perform_transformation']=True
        self['create_ww_links']=True
        self['ww_exist_alias']=('ONEWAY','WRONG_WAY')
        self['ww_change']={'FT':('+',100),'BIKE_CLASS':('*',0),'PER_RISE':('*',-1)}
        self['variable_transforms']={    
                                'MTYPE_NUM'    :('MTYPE',        {'SF':1,'MTC':0}    ,    ""        ),
                                'B0'        :('BIKE_CLASS',    {0:1,1:0,2:0,3:0}        ,    "int"    ),
                                'B1'        :('BIKE_CLASS',    {0:0,1:1,2:0,3:0}        ,    "int"    ),
                                'B2'        :('BIKE_CLASS',    {0:0,1:0,2:1,3:0}        ,    "int"    ),
                                'B3'        :('BIKE_CLASS',    {0:0,1:0,2:0,3:1}        ,    "int"    ),
                                'BNE1'        :('BIKE_CLASS',    {0:1,1:0,2:1,3:1}        ,    "int"    ),
                                'BNE2'        :('BIKE_CLASS',    {0:1,1:1,2:0,3:1}        ,    "int"    ),
                                'BNE3'        :('BIKE_CLASS',    {0:1,1:1,2:1,3:0}        ,    "int"    ),
                                'TPER_RISE'    :('PER_RISE',    ('max',0)            ,    "float"    )
                            }
        self['relevant_variables']=['DISTANCE','FT','MTYPE_NUM','TPER_RISE','WRONG_WAY','B0','B1','B2','B3','BNE1','BNE2','BNE3']                    
                            
        for key in changes:
            self[key]=changes[key]
            
class OuterNetworkConfig(UserDict):
    """store network configuration data"""
    
    def __init__(self, changes={}):
        UserDict.__init__(self)
        self['data_dir']=r"bike_model_input"
        self['link_file']=os.path.join(self['data_dir'],'links.csv')
        self['node_file']=os.path.join(self['data_dir'],'nodes.csv')
        self['dist_var']='DISTANCE'
        self['dist_scl']=1/5280 #rescales with node distance x dist_scl= link distance
        self['max_centroid']=2454
        
        self['use_dual']=False
        
        self['perform_transformation']=True
        self['create_ww_links']=False
        self['variable_transforms']={    'MTYPE_NUM'    :('MTYPE',        {'SF':1,'MTC':0}    ,    ""        )
                            }
        self['relevant_variables']=['DISTANCE','FT','MTYPE_NUM']
        
        for key in changes:
            self[key]=changes[key]
            
class OutputConfig(UserDict):
    """store output configuration data"""
    
    def __init__(self,changes={}):
        UserDict.__init__(self)
        self['output_dir']=r"bike_model_output"
        self['filename_dict']={'pathID':'PathID.csv',
                            'pathLink':'PathLink.csv',
                            'estimation_data':'EstimationData.csv',
                            'bound_data':'Bound.csv',
                            'overlap_data':'Overlap.csv',
                            'matrix_data':'Matrix.csv',
                            'assign_data':'Assign.csv',
                            'holdback_file':'Holdback.csv',
                            'logsum_data':'BikeLogsum.h5',
                            'maxutil_data':'BikeMaxutil.h5'}
        self['output_type']=['estimation',
                             'bound',
                             'geographic',
                             'overlap',
                             'assign',
                             'holdback_sample',
                             'logsum']
        
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
        
        # self.set_time_dir()
        
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
            self['overlap_threshold']=0.9    # filter out routes that have an overlap above this
            self['overlap_var']='DISTANCE'    # network variable for calculating overlap
            
            """prior coefficient distribution parameters"""
            self['ext_bound']=True            # use same distribution for each observation (False is deprecated)
            self['only_bound']=False        # in prepare_estimation.py, only extract prior distribution rather 
                                            # than continuing to generate choice sets?
            self['bound_from_file']=True     # use distribution from file rather than extracting?
            self['bound_file']=r'bike_BoundPredict.csv' #file to use
            self['bound_file_override']=True # override variable configuration in this choice_set_config if using file?
            self['bounding_box_sample_size']=500 # max number of observations to sample
            self['tolerance']=0.01             # percentage threshold to stop binary search when extracting prior distribution
            self['log_prior']=True             # use log-uniform prior? (False means uniform prior)
            
            """variable configuration"""

            self['variables']=['DISTANCE','BNE1','BNE2','BNE3','WRONG_WAY','TPER_RISE','TURN']
                                            # network variables to use in choice set generation
            self['ref']='DISTANCE'            # reference variable (coef fixed to 1)
            self['ranges']={'BNE1':[0.0000001,1000.0],
                            'BNE2':[0.0000001,1000.0],
                            'BNE3':[0.0000001,1000.0],
                            'TPER_RISE':[0.00001,100000.0],
                            'WRONG_WAY':[0.0000001,1000.0],
                            'TURN':[0.0000001,1000.0]}    # large initial boundary intervals
            self['weights']={'BNE1':'DISTANCE',
                             'BNE2':'DISTANCE',
                             'BNE3':'DISTANCE',
                             'TPER_RISE':'DISTANCE',
                             'WRONG_WAY':'DISTANCE'} # to multiply each link attribute value by
            self['median_compare']=['TURN']    #extract these coefficients with others at their medians (must appear last in self['variables'])
            self['randomize_compare']=[] #extract these coefficients with link randomization (must appear last in self['variables'])
            
            """generate noisy output?"""
            self['verbose']=True
            
            """speed up by randomizing whole network in outer loop and performing searches in inner loop using only comparisons/additions"""
            self['inverted']=True             # should we?
            self['inverted_N_attr']=multiprocessing.cpu_count() # when link attributes were randomized
                                             # individually, this controlled the number of link
                                             # randomizations, now just set it to the number of processors
            self['inverted_N_param']=min(2,int(20.0/self['inverted_N_attr']))
                                             # when link attributes were randomized individually,
                                             # this controlled the number of parameters to draw per link                                 
                                             # randomization, now just set it to the number of parameters
                                             # desired divided by the number of processors (e.g. w/; 
                                             # N_attr=4 processors x N_param=5 == 20 random parameters)
            self['inverted_nested']=False     # when link attributes were randomized individually, True 
                                             # would nest the attribute and parameter randomization 
                                             # loops, now just leave set to False
            
            self['inverted_multiple']=2      # use x times as many random seeds as needed for each source
        
            """link randomization parameters"""
            self['randomize_after']=True     # apply link randomization after generalized cost is
                                             # calculated rather than to attributes individually?
                                             # Leave set to True.
            self['randomize_after_dev']=0.4     # link randomization scale parameter
            self['randomize_after_iters']=3     # number of link randomizations per coefficient 
                                             # (e.g. 20 random parameters x 3 randomize_after_iters = 
                                             # 60 max choice set size)

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
        
class AssignConfig(UserDict):
    """compile configuration data"""
    
    def __init__(self, changes={}):
        UserDict.__init__(self)
        
        """how to project outer trips to the county line"""
        self['max_inner']=981                 # maximum zone id for SF county
        self['skip_zones']=[305,313,384,385]  # skip these; they don't connect.  TODO: make this automatic
        self['outer_importance_conditions']=[(982,1348),(2403,2455)]    #zones with non-negligible trips to SF
        self['boundary_condition']='MTYPE_NUM'# network variable that indicates links which are inside SF
        self['outer_impedance']="DISTANCE"       # network variable to minimize when projecting trips to county line
        
        """trip matrices to assign"""
        self['matrix_filenames']=[r"bike_model_input\triptable_AM.csv",
                                  #r"bike_model_input\triptable_md.csv",
                                  r"bike_model_input\triptable_PM.csv",
                                  #r"bike_model_input\triptable_ev.csv",
                                  #r"bike_model_input\triptable_ea.csv"
                            ]
        self['load_names']=['BIKE_AM','BIKE_PM']#'BIKE_MD','BIKE_EV','BIKE_EA'
        
        """override bound_file from choice_set_config"""
        self['bound_file']=r'bike_BoundPredict.csv'

        """path storage"""
        self['pickle_path']='C:/bike_pickle_path'    #directory to store path files
        self['delete_paths']=False    #delete the paths after assignment is complete?
        self['load_paths_from_files']=True    #use already generated paths rather than starting anew?
        
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
        self['divisors']={'TURNS_P_MI':'DISTANCE'}    # calculate this alias by dividing by this variable
        
        """fixed coefficients"""
        self['fixed_coefficients']=['DISTANCE','TURNS_P_MI','WRONG_WAY','BIKE_PCT_1','BIKE_PCT_2','BIKE_PCT_3','AVG_RISE','lnpathsize']
        self['alpha']=[-1.05,-0.21,-13.30,1.89,2.15,0.35,-154.0,1.0]
        # these are for visualizing how much each component contributes to the utility
        self['fixed_categories']  =['DISTANCE','TURNS_P_MI', 'WRONG_WAY','CLASS',    'CLASS',     'CLASS',     'SLOPE',   'lnpathsize']
        self['fc_unique'] = sorted(set(self['fixed_categories']))

        
        """random coefficients"""
        self['use_random_coefficients']=False
        self['random_coefficients']=[]#['BIKE_PCT_1','BIKE_PCT_2','BIKE_PCT_3','AVG_RISE']
        self['random_transformations']=[]#[idenfun,idenfun,idenfun,idenfun]
        self['latent_mu']=[]#[1.82,2.49,0.76,-2.22]
        self['latent_sigma']=array([])
        """array( [    [24.95,    0.,    6.58,    0.    ],
                                [0.,        5.45,    2.91,    0.    ],
                                [0.,        0.,    4.19,    0.    ],
                                [0.,        0.,    0.,    3.85    ]    ] )"""
        self['mixing_granularity']=0.2 # number of trips to simulate as an individual
        
        """for debugging code"""
        self['test_small_matrix']=False
    
        for key in changes:
            self[key]=changes[key]
            
def idenfun(x):
    return x
    
def negexp(x):
    return -exp(x)
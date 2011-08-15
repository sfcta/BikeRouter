from numpy import *
import numpy.random as nr
from math import exp

def simulate_mixed_logit(num_pers,predict_data,config):
	
	num=num_pers
	to_load=zeros(len(predict_data))
	while num>0:
		exputils=zeros(len(predict_data))
		for path_idx in range(len(predict_data)):
			vals=predict_data[path_idx]
			u=0
			for i in range(len(config['fixed_coefficients'])):
				u=u+config['alpha'][i]*vals[config['fixed_coefficients'][i]]
		
			if config['use_random_coefficients']:
				beta=nr.multivariate_normal(config['latent_mu'],config['latent_sigma'])
				for i in range(len(beta)):
					beta[i]=config['random_transformations'][i](beta[i])
					u=u+beta[i]*vals[config['random_coefficients'][i]]

			exputils[path_idx]=exp(u)
		
		if num>config['mixing_granularity'] and config['use_random_coefficients']:
			to_load=to_load+config['mixing_granularity']*exputils/sum(exputils)
		else:
			to_load=to_load+num*exputils/sum(exputils)

		if config['use_random_coefficients']:
			num=num-config['mixing_granularity']
		else:
			num=0
		
	return to_load
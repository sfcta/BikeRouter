import os, random
from UserDict import UserDict

class LinkRandomizer(UserDict):
	"""set up randomization parameters and generate random link attributes"""
	
	def __init__(self):
		"""default setup is beta-uniform"""
		UserDict.__init__(self)
		
		self['variables']=[]
		self['zero']={}
		self['pos']={}
		
	def get_link_distribution(self,G):
		"""extract percentage of links that are zero and the positive conditional mean for each attribute"""
		
		self['zero']['probs']={}
		self['pos']['means']={}
		
		for key in self['variables']:
			zero_edges=G.select_edges_where(key,'==',0.,False)
			self['zero']['probs'][key]=float(len(zero_edges))/G.size()
			nonzero_edges=G.select_edges_where(key,'!=',0.,True)
			avg=0
			for e in nonzero_edges:
				avg=avg+e[2][key]
			self['pos']['means'][key]=float(avg)/len(nonzero_edges)
		
	def set_scl(self,scl):
		
		self['zero']['scl']=scl
	
	def set_fam(self,zero_fam,pos_fam):
		
		self['pos']['fam']=pos_fam
		self['zero']['fam']=zero_fam
	
	def set_par(self,zero_par,pos_par):

		self['zero']['par']=zero_par
		self['pos']['par']=pos_par
		
	def get_fam_means(self):
		"""calculate means for the given family and parameters"""
		
		zero_mu=0
		pos_mu=0
		for i in range(1000):
			zero_mu=zero_mu+self['zero']['fam'](*self['zero']['par'])
			pos_mu=pos_mu+self['pos']['fam'](*self['pos']['par'])
		self['zero']['mean']=zero_mu/1000
		self['pos']['mean']=pos_mu/1000
		
	def update_denoms(self):
		"""find the denominator that normalizes the randomization"""
		
		self.get_fam_means()
		
		self['denoms']={}
		
		for key in self['variables']:
			self['denoms'][key]=self['pos']['mean'] + self['zero']['mean'] * self['zero']['scl'] * self['zero']['probs'][key]/ (1-self['zero']['probs'][key])

	def generate_value(self,G,a,b,key):
		"""generate one randomized link value"""
		
		val=G[a][b][key]
		
		if 'no_randomize' in self:
			if key in self['no_randomize']:
				return val
		
		if val==0:
			
			return 1/self['denoms'][key] * self['zero']['scl'] * self['zero']['fam'](*self['zero']['par'])
			
		else:
			
			return 1/self['denoms'][key] * val * self['pos']['fam'](*self['pos']['par'])
	
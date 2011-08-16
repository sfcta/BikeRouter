#!/usr/bin/env python

'''finds single-source SP for a graph with no negative costs.
'''

import heapq, random

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

def single_source_dijkstra(G,source,varname,exclude_group=[],
						   target=None,weights={},link_randomizer=None,
						   allow_centroids=False,target_type=0,verbose=False):
	"""Finds the single-source shortest path for a graph with given nonnegative edge costs.
	If target is specified, finds the shortest path to the target; otherwise, finds the shortest
	path to all other nodes.
	
	Inputs:
	G        		is the graph, which is a TransportNetwork
	source   		is the source node number
	varname  		is what?
	exclude_group 	?
	target			dictionary: target node num to distance (?)
	weights			?
	link_randomizer ?
	allow_centroids ?
	target_type		for dictionary targets,
						target_type 0 means all must be reached, 
	                  	target_type 1 means any can be reached and function will return node
	                  	reached as third output
	verbose			?
	
	Returns (dist,paths,[v]) where
	dist			is a dictionary, target -> final distance
	paths			is a dictionary, target -> shortest path
	v				returned if target_type is 1; target node reached
	"""
	# import pydevd; pydevd.settrace()
	
	randomize_after=(type(link_randomizer)==type(0.0))
	
	_target=target.copy()
	
	if source==_target: return (0, [source])
	dist = {}  # dictionary of final distances
	paths = {source:[source]}  # dictionary of paths
	seen = {source:0} 
	fringe=[] # use heapq with (distance,label) tuples 
	heapq.heappush(fringe,(0,source))
	
	target_is_dict=(type(_target)==type({}))
	while fringe and (_target is None or _target):
		(d,v)=heapq.heappop(fringe)
		if verbose:
			print v
		if v in dist: continue # already searched this node.
		dist[v] = d
		if target_is_dict and v in _target:
			if verbose:
				print "REMOVED FROM TARGET"
			del _target[v]
			if target_type==1:
				return (dist,paths,v)
		if v == _target or _target=={}:
			break

		v_centroid=False
		v_contains_source=False
		if type(v)==type((1,2)):
			for a in v:
				if a <= G.config['max_centroid'] :
					v_centroid=True
				if a==source:
					v_contains_source=True
		else:
			if v <= G.config['max_centroid'] :
				v_centroid=True
			if v==source:
				v_contains_source=True
		
		if verbose:
		    print "Neighbors:",
		for w,edgedata in G[v].iteritems():
			if verbose:
			    print w
			 
			 #if single variable
			if type(varname)==type(str()):
				wgt=1
				if varname in weights:
					wgt=G[v][w][weights[varname]]
				vw_dist= dist[v] + wgt*edgedata[varname]

			#if generalized costs
			elif type(varname)==type({}):
				vw_dist=dist[v]

				add_length
				for key in varname:
					wgt=1
					if key in weights:
						wgt=G[v][w][weights[key]]
						
					if link_randomizer is not None and not randomize_after and ( ( type(v)==type(1) or type(w)==type((1,2)) ) or G.orig_network is None):
						add_length=add_length+wgt*varname[key]*link_randomizer.generate_value(G,v,w,key)
					else:
						add_length=add_length+wgt*varname[key]*edgedata[key]
						
				if randomize_after:
					add_length=add_length*random.uniform(1-link_randomizer,1+link_randomizer)
					
				vw_dist=vw_dist+add_length
			
			else:
				raise TypeError, "varname must be string or dictionary"

			if w in dist:
				if vw_dist < dist[w]:
					raise ValueError,\
						  "Contradictory paths found: negative weights?"
			else:
				w_centroid=False
				gateway=False
				if type(w)==type((1,2)):
					for a in w:
						if a <= G.config['max_centroid'] :
							w_centroid=True
				else:
					if w <= G.config['max_centroid'] :
						w_centroid=True
						gateway=True
				if (w not in seen or vw_dist < seen[w]) and (v_contains_source or (not v_centroid) or gateway or allow_centroids) and ((v,w) not in exclude_group): 
					seen[w] = vw_dist
					heapq.heappush(fringe,(vw_dist,w))
					paths[w] = paths[v]+[w]
					
	return (dist,paths)
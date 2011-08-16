#!/usr/bin/env python

'''shortest path using basic a_star
'''

import heapq

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

def a_star(G, start, goal, heuristic, varname, exclude_group=[]):
	"""shortest path using basic a_star"""
	
	# The queue stores priority, node, cost to reach, and parent.
	queue = [(0, start, 0, None)]

	# This dictionary maps enqueued nodes to distance of discovered paths
	# and the computed heuristics to goal. We avoid to compute the heuristics
	# more than once and to insert too many times the node in the queue.
	enqueued = {}

	# This maps explored nodes to parent closest to the start
	explored = {}
	
	while queue:
		_, curnode, dist, parent = heapq.heappop(queue)
		
		if curnode == goal:
			path = [curnode]
			node = parent
			while node is not None:
				path.append(node)
				node = explored[node]
			path.reverse()
			return path

		if curnode in explored:
			continue

		explored[curnode] = parent

		#skip centroid connectors not coming from start
		if (curnode != start) and (curnode <=G.config['max_centroid']):
			continue

		for neighbor, w in G[curnode].iteritems():
			if (neighbor in explored) or ((curnode,neighbor) in exclude_group):
				continue

			ncost = dist + w[varname]

			if neighbor in enqueued:
				qcost, h = enqueued[neighbor]
				if qcost <= ncost:
					continue
				# if ncost < qcost, a longer path to neighbor remains
				# enqueued. Removing it would need to filter the whole
				# queue, it's better just to leave it there and ignore
				# it when we visit the node a second time.
			else:
				h = heuristic(neighbor, goal)
			
			enqueued[neighbor] = ncost, h
			heapq.heappush(queue, (ncost + h, neighbor, ncost, curnode))

	return None
	
	

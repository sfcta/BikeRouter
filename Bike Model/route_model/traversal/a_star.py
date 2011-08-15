import heapq

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

import unittest
from route_model.config.network_config import NetworkConfig
from route_model.transport_network import TransportNetwork

class Tests(unittest.TestCase):
	
	def setUp(self):
		
		network_config=NetworkConfig()
	
		self.net=TransportNetwork(network_config)
		self.net.create_node_xy_from_csv(network_config)

	def testAStarKnownValues(self):
		"""a_star should give known result with known input"""
		x=a_star(self.net, 1, 4, self.net.euclid, 'DISTANCE')
		self.assertEqual(x,[1,2,4])
		
	def testAStarExcludeGroupKnownValues(self):
		"""a_star should give known result with known input and exclude group"""
		x=a_star(self.net, 1, 4, self.net.euclid, 'DISTANCE',exclude_group=[(1,2)])
		self.assertEqual(x,[1,3,4])
		
	def testAStarNoPath(self):
		"""a_star should return None if no path exists"""
		x=a_star(self.net, 1, 4, self.net.euclid, 'DISTANCE',exclude_group=[(1,2),(1,3)])
		self.assertEqual(x,None)

if __name__ == '__main__':
	
	unittest.main()
	
	

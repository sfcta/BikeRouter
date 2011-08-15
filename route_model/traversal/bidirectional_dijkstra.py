import heapq, time, random

def bidirectional_dijkstra(G, source, target,varname,weights={},link_randomizer=None):
    """Dijkstra's algorithm for shortest paths using bidirectional search.
    varname can be a dictionary of generalized cost coefficients"""
    
    randomize_after=(type(link_randomizer)==type(0.0))
    
    if source is None or target is None:
        raise NetworkXException(
            "Bidirectional Dijkstra called with no source or target")
            
    if source == target: return (0, [source])
        
    if G.orig_network is not None:
        for neighbor in G.orig_network.successors_iter(source):
            G.add_edge(source,(source,neighbor),dict(G.orig_network[source][neighbor],**{'TURN':0,'R_TURN':0,'L_TURN':0}))
        for neighbor in G.orig_network.predecessors_iter(target):
            new_data=dict(G.orig_network[neighbor][target],**{'TURN':0,'R_TURN':0,'L_TURN':0})
            for key in new_data:
                new_data[key]=0
            G.add_edge((neighbor,target),target,new_data)
        
    #Init:   Forward             Backward
    dists =  [{},                {}]# dictionary of final distances
    paths =  [{source:[source]}, {target:[target]}] # dictionary of paths 
    fringe = [[],                []] #heap of (distance, node) tuples for extracting next node to expand
    seen =   [{source:0},        {target:0} ]#dictionary of distances to nodes seen 
    #initialize fringe heap
    heapq.heappush(fringe[0], (0, source)) 
    heapq.heappush(fringe[1], (0, target))
    #neighs for extracting correct neighbor information
    if G.is_directed():
        neighs = [G.successors_iter, G.predecessors_iter]
    else:
        neighs = [G.neighbors_iter, G.neighbors_iter]
    #variables to hold shortest discovered path
    #finaldist = 1e30000
    finalpath = []
    dir = 1
    while fringe[0] and fringe[1]:
        # choose direction 
        # dir == 0 is forward direction and dir == 1 is back
        dir = 1-dir
        # extract closest to expand
        (dist, v )= heapq.heappop(fringe[dir]) 
        if v in dists[dir]:
            # Shortest path to v has already been found 
            continue
        # update distance
        dists[dir][v] = dist #equal to seen[dir][v]
        if v in dists[1-dir]:
            # if we have scanned v in both directions we are done 
            # we have now discovered the shortest path
            if G.orig_network is not None:
                for neighbor in G.orig_network.successors_iter(source):
                    G.remove_edge(source,(source,neighbor))
                for neighbor in G.orig_network.predecessors_iter(target):
                    G.remove_edge((neighbor,target),target)            
            return (finaldist,finalpath)
        
        v_centroid=False
        if type(v)==type((1,2)):
            for n in v:
                if n <= G.config['max_centroid'] :
                    v_centroid=True
        else:
            if v <= G.config['max_centroid'] :
                v_centroid=True

        #####################################
        for w in neighs[dir](v):
            if(dir==0): #forward
                a=v
                b=w
            else: #back, must remember to change v,w->w,v
                a=w
                b=v
            
            #if single variable
            if type(varname)==type(str()):
                if varname in weights:
                    wgt=G[a][b][weights[varname]]
                    vwLength = dists[dir][v] + wgt*G[a][b][varname]
                else:
                    vwLength = dists[dir][v] + G[a][b][varname]
            
            else:
                #if generalized costs
                if type(varname)==type({}):
                    vwLength=dists[dir][v]
                    
                    add_length=0
                    for key in varname:
                        wgt=1
                        if key in weights:
                            wgt=G[a][b][weights[key]]
                        
                        if link_randomizer is not None and not randomize_after and ( ( type(a)==type(1) or type(b)==type((1,2)) ) or G.orig_network is None):
                            add_length=add_length+wgt*varname[key]*link_randomizer.generate_value(G,a,b,key)
                        else:
                            add_length=add_length+wgt*varname[key]*G[a][b][key]
                    
                    if randomize_after:
                        add_length=add_length*random.uniform(1-link_randomizer,1+link_randomizer)
                        
                    vwLength=vwLength+add_length
                        
                else:
                    raise TypeError, "varname must be string or dictionary"
        #####################################

            if w in dists[dir]:
                if vwLength < dists[dir][w]:
                    raise ValueError,\
                        "Contradictory paths found: negative weights?"
            ###################################
            else:
                w_centroid=False
                if type(w)==type((1,2)):
                    for n in w:
                        if n <= G.config['max_centroid'] :
                            w_centroid=True
                else:
                    if w <= G.config['max_centroid'] :
                            w_centroid=True
                if (w not in seen[dir] or vwLength < seen[dir][w]) and (v==source or v==target or not v_centroid) and (w==source or w==target or not w_centroid): 
                ###################################
                # relaxing        
                    seen[dir][w] = vwLength
                    heapq.heappush(fringe[dir], (vwLength,w)) 
                    paths[dir][w] = paths[dir][v]+[w]
                    if w in seen[0] and w in seen[1]:
                        #see if this path is better than than the already
                        #discovered shortest path
                        totaldist = seen[0][w] + seen[1][w] 
                        if finalpath == [] or finaldist > totaldist:
                            finaldist = totaldist
                            revpath = paths[1][w][:]
                            revpath.reverse()
                            finalpath = paths[0][w] + revpath[1:]
    print 'WARNING: no path'
    if G.orig_network is not None:
        for neighbor in G.orig_network.successors_iter(source):
            G.remove_edge(source,(source,neighbor))
        for neighbor in G.orig_network.predecessors_iter(target):
            G.remove_edge((neighbor,target),target)            
    return False
    
import unittest
from route_model.config.network_config import NetworkConfig
from bike_model.config.bike_network_config import BikeNetworkConfig
from route_model.transport_network import TransportNetwork

class Tests(unittest.TestCase):
    
    def setUp(self):
        
        network_config=NetworkConfig()
        self.net=TransportNetwork(network_config)
        self.net.create_node_xy_from_csv(network_config)

        bike_network_config=BikeNetworkConfig()
        self.bikenet=TransportNetwork(bike_network_config)
        self.bikenet.create_node_xy_from_csv(bike_network_config)


    def testBDDijkstraKnownValues(self):
        """BiDirectionalDijkstra should give known result with known input"""
        dist,path=bidirectional_dijkstra(self.net, 1,4, 'DISTANCE')
        self.assertEqual(path,[1,2,4])

    def testBDDijkstraGeneralized(self):
        """BiDirectionalDijkstra should work with generalized cost"""
        dist,path=bidirectional_dijkstra(self.bikenet, 259, 226,{'DISTANCE':1,'B0':2})
        print path
        
    def testBDDijkstraWeights(self):
        """BiDirectionalDijkstra should work with weights"""
        dist,path=bidirectional_dijkstra(self.bikenet, 259, 226,{'DISTANCE':1,'B0':2},weights={'B0':'DISTANCE'})
        print path
        
    def testBDDijkstraTime(self):
        """BiDirectionalDijkstra should terminate in reasonable time"""
        t1=time.time()
        dist,path=bidirectional_dijkstra(self.bikenet, 259, 226,{'DISTANCE':1,'B0':2},weights={'B0':'DISTANCE'})
        t2=time.time()
        print t2-t1

if __name__ == '__main__':
	
	unittest.main()
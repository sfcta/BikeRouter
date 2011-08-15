from route_model.misc import get_orig_path

def path_size(G,choice_sets,choice_set_config):
	
	result=[]
	config=choice_set_config
	
	the_network=G
	if G.orig_network is not None:
		the_network=G.orig_network
	
	for path_list in choice_sets:
		
		temp=[]
		
		hashes=[]; lengths=[]
		for cur_path in path_list:
			use_path=cur_path
			if G.orig_network is not None:
				use_path=get_orig_path(cur_path)
			cur_hash={}
			cur_length=0
			for i in range(len(use_path)-1):
				cur_hash[(use_path[i],use_path[i+1])]=the_network[use_path[i]][use_path[i+1]][config['overlap_var']]
				cur_length=cur_length+cur_hash[(use_path[i],use_path[i+1])]
			hashes.append(cur_hash)
			lengths.append(cur_length)
		min_length=min(lengths)

		for i in range(len(path_list)):
			PS=0
			for a in hashes[i]:
				delta_sum=0
				for j in range(len(path_list)):
					if a in hashes[j]:
						delta_sum=delta_sum+min_length/lengths[j]
				PS=PS+hashes[i][a]/lengths[i]/delta_sum
			temp.append(PS)
		
		result.append(temp)
		
	return result
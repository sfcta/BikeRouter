def path_trace(G,path,varname,tracefun='sum',finalfun=None,wgtvar=None):
	"""tracefun is one of 'sum', 'min', 'max', 'avg'
	finalfun is one of None, 'inv' for inverse, 'neg' for negative
	wgtvar is the name of the variable for weighting sums, avgs, if desired"""
	
	L=len(path)-1
	sum_val=0
	min_val=None
	max_val=None
	wgt_sum=0
	if G.orig_network is not None:
		L=L-1
	for i in range(L):
		wgt_val=1
		
		if G.orig_network is None :
			# if network is not pseudo-dual, need to calculate turns on fly
			if varname in ['TURN','L_TURN','R_TURN','U_TURN']:
				trace_val=0
				if i<(L-1) and i>0:
					turn_dir=G.turn_dir((path[i],path[i+1]),(path[i+1],path[i+2]))
					if turn_dir:
						if varname=='TURN':
							trace_val=1
						if varname=='R_TURN' and turn_dir=='R':
							trace_val=1
						if varname=='L_TURN' and turn_dir=='L':
							trace_val=1
						if varname=='U_TURN' and turn_dir=='U':
							trace_val=1
			else:
				trace_val = G[path[i]][path[i+1]][varname]
				if wgtvar is not None:
					wgt_val = G[path[i]][path[i+1]][wgtvar]
		else:
			# need to handle first link of pseudo-dual separately
			if i>0:
				trace_val = G[path[i]][path[i+1]][varname]
				if wgtvar is not None:
					wgt_val = G[path[i]][path[i+1]][wgtvar]
			else:
				if varname in ['TURN','L_TURN','R_TURN','U_TURN']:
					trace_val=0
				else:
					trace_val = G.orig_network[path[i+1][0]][path[i+1][1]][varname]
				if wgtvar is not None:
					wgt_val = G.orig_network[path[i+1][0]][path[i+1][1]][wgtvar]
		
		trace_val=trace_val*wgt_val
		wgt_sum=wgt_sum+wgt_val
		sum_val=sum_val+trace_val
		min_val=min(min_val,trace_val)
		max_val=max(max_val,trace_val)
		
	if wgtvar is None:
		wgt_sum=L
	if tracefun=='sum':
		return_val=sum_val
	if tracefun=='min':
		return_val=min_val
	if tracefun=='max':
		return_val=max_val
	if tracefun=='avg':
		if wgt_sum==0 and sum_val==0:
			return_val=0
		else:
			return_val=sum_val/wgt_sum
	if finalfun=='inv':
		return 1/return_val
	if finalfun=='neg':
		return -return_val
	return return_val
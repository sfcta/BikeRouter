from math import *

def get_class_instance_from_python_path(python_path):
	camel_case=get_camel_case_class_name_from_python_path(python_path)
	stmt='from %s import %s' % (python_path, camel_case)
	exec(stmt)

	stmt='config=%s()' % camel_case
	exec(stmt)
	return config
	
def get_camel_case_class_name_from_python_path(python_path):
	class_name=python_path.split('.')[-1]
	camel_case=''.join(map(lambda s: s.capitalize(), class_name.split('_')))
	return camel_case
	
def get_time_dependent_variable(variable,trip_time,time_dependent_relation):
	
	if time_dependent_relation is None:
		time_dep_var=variable
	else:
		if variable in time_dependent_relation:
			for rule in time_dependent_relation[variable]:
				if rule[0]=='else':
					time_dep_var=rule[1]
				elif trip_time>=rule[0][0] and trip_time<rule[0][1]:
					time_dep_var=rule[1]
					break
		else:
			time_dep_var=variable
		
	return time_dep_var
	
def get_inverse_time_dependent_relation(time_dependent_relation):
	inverse_time_dependent_relation={}
	for prelim_var in time_dependent_relation:
		for rule in time_dependent_relation[prelim_var]:
			inverse_time_dependent_relation[rule[1]]=prelim_var
	return inverse_time_dependent_relation
	
def get_dual_path(orig_path):
	
	dual_path=[orig_path[0]]
	for i in range(len(orig_path)-1):
		dual_path.append((orig_path[i],orig_path[i+1]))
	dual_path.append(orig_path[-1])
		
	return dual_path
	
def get_orig_path(dual_path):
	
	orig_path=[dual_path[1][0]]
	for i in range(1,len(dual_path)-1):
		orig_path.append(dual_path[i][1])
		
	return orig_path
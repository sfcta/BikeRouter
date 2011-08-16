#!/usr/bin/env python

'''defines how to read various import data
'''

import csv, glob, os
import numpy

__author__ = "Jeff Hood, San Francisco County Transportation Authority"
__license__= "GPL"
__email__  = "modeling@sfcta.org"
__date__   = "June 2010"

def read_trip_data(filename):
	infile=open(filename)
	reader=csv.reader(infile)
	
	trip_data={}
	header={}
	count=0
	for row in reader:
		count=count+1
		if count==1:
			for i in range(len(row)):
				header[row[i]]=i
			continue
		if int(row[header['trip_id']]) not in trip_data:
			trip_data[int(row[header['trip_id']])]=[int(row[header['a']]),int(row[header['b']])]
		else:
			trip_data[int(row[header['trip_id']])].append(int(row[header['b']]))
			
	infile.close()

	return trip_data
	
def read_trip_data_from_matsim(dirname):
	
	trip_data={}
	for f in glob.glob(os.path.join(dirname, '*.*')):
		#print f
		infile=open(f)
		reader=csv.reader(infile,dialect='excel-tab')
		
		count=0
		for row in reader:
			count=count+1
			if count>1:
				trip_data[tuple(row[0:3])]=row[9:-1]
				
		infile.close()
		
	for key in trip_data:
		for i in range(len(trip_data[key])):
			trip_data[key][i]=int(trip_data[key][i])
			
	return trip_data
	
def read_time(filename):
	infile=open(filename)
	reader=csv.reader(infile)
	
	context_data={}
	count=0
	for row in reader:
		count=count+1
		if count==1:
			continue
		for i in range(1,len(row)):
			context_data[row[0]]=float(row[i])
			
	infile.close()

	return context_data
	
def read_bound(filename,return_ranges=False):
	infile=open(filename)
	reader=csv.reader(infile)
	
	ext_bound={}
	weights={}
	ranges={}
	count=0
	for row in reader:
		count=count+1
		if count>1:
			ext_bound[row[0]]=(float(row[4]),float(row[5]))
			ranges[row[0]]=(float(row[2]),float(row[3]))
			if row[1] != 'None':
				weights[row[0]]=row[1]
	infile.close()

	if return_ranges:
		return ext_bound,weights,ranges
	else:
		return ext_bound,weights
	
def read_matrix(filename, headerline=True):
	""" Returns float32 numpy array representing the given csv matrix
	"""
	infile=open(filename,'rU')
	reader=csv.reader(infile)
	
	data=list(reader)
	infile.close()
	
	matrix=[]
	start = 0
	if headerline: start = 1
	for row in data[start:]:
		matrix.append(row[1:])
		
	return numpy.array(matrix,dtype="float32")
	
def read_holdback(filename):
	infile=open(filename,'rU')
	reader=csv.reader(infile)
	
	holdback_sample=set()
	
	data=list(reader)
	infile.close()
	
	for row in data[1:]:
		holdback_sample.add(row[0])
		
	return holdback_sample
		
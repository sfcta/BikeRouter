import os, csv, sys, glob, logging

# enable import bikeAssign.*
scriptsdir = os.path.realpath(os.path.join(os.path.split(__file__)[0], os.pardir))
sys.path.insert(0,scriptsdir)

# enable the use of the config argument 
sys.path.insert(0,os.getcwd())
print sys.path

from optparse import OptionParser
import bikeAssign.misc as rm_misc
import bikeAssign.input as rm_input
import bikeAssign.output as rm_output
from transport_network import TransportNetwork, create_pseudo_dual
from bikeAssign.choice_set.generate_choice_set import generate_choice_set
import bikeAssign.choice_set.ds_generate as ds
from bikeAssign.assign.project_outer_trips import project_outer_trips
import time
from multiprocessing import Lock, Process, current_process, Queue, Manager
from bikeAssign.choice_set.path_size import path_size
from bikeAssign.assign.simulate_mixed_logit import simulate_mixed_logit
from math import log, exp
from bikeAssign.path_trace import path_trace
import random
from bikeAssign.traversal.single_source_dijkstra import single_source_dijkstra
import cPickle, glob
from time import time, localtime, strftime
from numpy import *

def trace_and_load(network, filtered_sets, master_config, matrix_list, source):
    """
    Loads the trip tables onto the passed in network.
    Also returns the logsums 
    """
    config = master_config.assign_config
    this_network = network

    #trace
    logging.info(current_process().name + "- zone: " + str(source) + " Tracing paths...")
    predict_collection = {}
    for target in filtered_sets:
        predict_data = []
        for path in filtered_sets[target]: # for each path from source to target, fill in the predict data with the relevant variables. e.g. predict_data=[ {dict of variable=> path1_variable_vals}, {dict of variable => path2_variable_vals}, ... ]
            trace_vals = {}
            for i in range(len(config['variables'])):
                var = config['variables'][i]
                trace_vals[config['aliases'][i]] = path_trace(this_network, path, var, config['trace_funs'][i], config['final_funs'][i], config['weights'][i])
            for var in trace_vals:    
                if var in config['divisors']:
                    trace_vals[var] = trace_vals[var] / trace_vals[config['divisors'][var]]
            predict_data.append(trace_vals)
        if config['path_size']:
            PS = path_size(this_network, [filtered_sets[target]], master_config.choice_set_config).pop()
            for i in range(len(filtered_sets[target])):
                if config['path_size_log']:
                    PS[i] = log(PS[i])
                predict_data[i][config['path_size_alias']] = PS[i]
        predict_collection[target] = predict_data
    
    #apply logit probabilities
    logging.info(current_process().name + "- zone: " + str(source) + " Applying logit probabilities...")
    
    to_load = []
    logsums = [] # logsums = [ mat1logsums, mat2logsums ]
    maxutils= [] # maxutils = [ mat1maxutils, mat2maxutils ]
    
    maxutil_components = {} # {component1:[max1utils, max2utils], ...}
    for uc in config["fc_unique"]: maxutil_components[uc] = []

    for mat_idx in range(len(matrix_list)):
        to_load.append({})
        logsums.append([0.0]*matrix_list[mat_idx].shape[0])
        maxutils.append([0.0]*matrix_list[mat_idx].shape[0])
        for uc in config["fc_unique"]: maxutil_components[uc].append([0.0]*matrix_list[mat_idx].shape[0])
        
        for target in predict_collection:
            num_pers = matrix_list[mat_idx][source - 1, target - 1]
            (to_load[mat_idx][target],
             logsums[mat_idx][target-1],
             maxutils[mat_idx][target-1],
             maxutil_components_temp) = simulate_mixed_logit(num_pers, predict_collection[target], config)
            for uc in config["fc_unique"]: 
                maxutil_components[uc][mat_idx][target-1] = maxutil_components_temp[uc]
    
    #load onto network
    logging.info(current_process().name + "- zone: " + str(source) + " Loading network...")
    for target in filtered_sets:
        for j in range(len(filtered_sets[target])):
            path = filtered_sets[target][j]
            if this_network.orig_network is None:
                for i in range(len(path) - 1):
                    for mat_idx in  range(len(matrix_list)):
                        this_network[path[i]][path[i + 1]][config['load_names'][mat_idx]] = this_network[path[i]][path[i + 1]][config['load_names'][mat_idx]] + to_load[mat_idx][target][j]
            else:
                for i in range(1, len(path) - 1):
                    for mat_idx in  range(len(matrix_list)):
                        this_network.orig_network[path[i][0]][path[i][1]][config['load_names'][mat_idx]] = this_network.orig_network[path[i][0]][path[i][1]][config['load_names'][mat_idx]] + to_load[mat_idx][target][j]
    return (logsums, maxutils, maxutil_components)

def assign_worker(work_queue, done_queue, network, master_config, ext_bound, matrix):
    this_network = network
    config = master_config.assign_config
    
    #initialize link randomizer
    link_randomizer = None
    if master_config.choice_set_config['method'] == 'doubly_stochastic' and not master_config.choice_set_config['randomize_after']:
        print strftime("%x %X", localtime()) + ": ", current_process().name, "Initializing link randomizer..."
        link_randomizer = master_config.choice_set_config.get_link_randomizer(this_network, master_config)
    
    if master_config.choice_set_config['method'] == 'doubly_stochastic' and master_config.choice_set_config['randomize_after']:
        link_randomizer = master_config.choice_set_config['randomize_after_dev']
    
    idx = 0
    for source, the_target in iter(work_queue.get, 'STOP'):
        idx = idx + 1
        print strftime("%x %X", localtime()) + ": ", current_process().name, "-", idx, ". zone: ", source, "Generating sets..."
        
        if source in the_target:
            del the_target[source]
        
        filtered_sets = ds.ds_generate_single_source(this_network, source, the_target, master_config.choice_set_config, link_randomizer, ext_bound)
        
        trace_and_load(this_network, filtered_sets, master_config, matrix, source)
    
    done_queue.put(this_network.orig_network)
    done_queue.put('STOP')
    return True

def inverted_assignment_search_worker(work_queue, done_queue, network, master_config, ext_bound, st_dict, seed_selections):
    """
    TODO:MAKE THIS SPHINX
    INPUTS
    work_queue: contains a list of tuples derived from st_dict dictionary sourcezone , { targetzone1:1 targetzone2:1 ...}
                generally this starts with every OD
    done_queue: some network copy???
    network   :
    master_config:
    ext_bound : i.e. 'bike_BoundPredict.csv'
    st_dict   : source zone - target zone dictionary, shows which ODs to get paths for
    seed_selections ={<source zone>:[list of random seeds]}
    """

    logfile = "bike_model_output\\choice_set_gen-" + current_process().name + ".log"
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        filename=logfile,
                        filemode='a')
    logging.info('==============================================================================')
    logging.info("Started inverted_assignment_search_worker")
    # logging.debug("st_dict="+str(st_dict))
    
    try:

        if not master_config.choice_set_config['randomize_after'] :
            logging.info("Initializing link randomizer...")
            link_randomizer = master_config.choice_set_config.get_link_randomizer(network, master_config)
        
        rand_net = network.copy()
        rand_net.orig_network = None
        bounding_box = ext_bound
        varcoef = {}
        
        for i in iter(work_queue.get, 'STOP'):
            
            if master_config.choice_set_config['inverted_nested'] and not master_config.choice_set_config['randomize_after']:
                #randomize link values
                for e in rand_net.edges_iter():
                    for key in master_config.choice_set_config['variables']:
                        rand_net[e[0]][e[1]][key] = link_randomizer.generate_value(network, e[0], e[1], key)
                        
            #loop over number of parameter randomizations
            for j in range(master_config.choice_set_config['inverted_N_param']): #j is right now always zero it seems - TODO rename this variable!
                
                logging.info("Attr # %d Param # %d" % (i, j))
                
                if not master_config.choice_set_config['inverted_nested'] and not master_config.choice_set_config['randomize_after']:
                    #randomize link values
                    for e in rand_net.edges_iter():
                        for key in master_config.choice_set_config['variables']:
                            rand_net[e[0]][e[1]][key] = link_randomizer.generate_value(network, e[0], e[1], key)            
                        
                #sample generalized cost coefficients
                for key in bounding_box:
                    if master_config.choice_set_config['log_prior']:
                        varcoef[key] = exp(random.uniform(log(bounding_box[key][0]), log(bounding_box[key][1])))
                    else:
                        varcoef[key] = random.uniform(bounding_box[key][0], bounding_box[key][1])
                        
                logging.debug(varcoef)
                        
                #calculate generalized costs
                for e in rand_net.edges_iter():
                    rand_net[e[0]][e[1]]['gencost'] = 0
                    for key in varcoef:
                        wgt = 1
                        if key in master_config.choice_set_config['weights']:
                            wgt = network[e[0]][e[1]][master_config.choice_set_config['weights'][key]]
                        rand_net[e[0]][e[1]]['gencost'] = rand_net[e[0]][e[1]]['gencost'] + varcoef[key] * rand_net[e[0]][e[1]][key] * wgt
                        
                use_cost = 'gencost'
                to_iter = 1
                if master_config.choice_set_config['randomize_after']:
                    use_cost = 'usecost'
                    to_iter = master_config.choice_set_config['randomize_after_iters']
                    
                while to_iter:
                    to_iter = to_iter - 1
                    result_paths = {}
    
                    if master_config.choice_set_config['randomize_after']:
                        for e in rand_net.edges_iter():
                            rand_net[e[0]][e[1]]['usecost'] = rand_net[e[0]][e[1]]['gencost'] * random.uniform(1 - master_config.choice_set_config['randomize_after_dev'], 1 + master_config.choice_set_config['randomize_after_dev'])
    
                    for source in st_dict: 
                    
                        if seed_selections[source][i * master_config.choice_set_config['inverted_N_param'] + j]:
                            the_target = st_dict[source]  
                    
                            if source in the_target: 
                                del the_target[source] # delete if origin=destination
                        
                            every_path = single_source_dijkstra(rand_net, source, use_cost, target=the_target)[1] # returns the path
                    
                            target_paths = {}  #???why is this just copying?
                            for t in the_target:
                                if t in every_path:
                                    target_paths[t] = every_path[t]
                    
                            fname = os.path.join(master_config.assign_config['pickle_path'], str(source) + '_' + str(i) + '-' + str(j) + '_' + str(to_iter))
                            f = open(fname, 'wb')
                            cPickle.dump(target_paths, f, 1)
                            f.close()
                
        done_queue.put('STOP')
    
    except:
        logging.exception("Exception raised in inverted_assignment_search_worker")

    
    logging.info("Finished inverted_assignment_search_worker.")
    return True
    
def inverted_assignment_load_worker(work_queue, done_queue, network, master_config, ext_bound, matrix_list):
    """
    The *work_queue* contains a list of tuples, e.g. ``sourcezone => { targetzone1:1 targetzone2:1 ...}``
    The *done_queue* ?
    The *network* is the TransportNetwork
    The *matrix_list* is a list of trip table matrices to assign. 
      (e.g. ``matrix_list=[AM bike trip table, PM bike trip table]``)
    """
    logfile = "bike_model_output\\assignment-" + current_process().name + ".log"
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        filename=logfile,
                        filemode='a')
    logging.info('==============================================================================')
    logging.info("Started inverted_assignment_load_worker")
    
    this_network = network
    config = master_config.assign_config
    
    idx = 0
    
    logsums = []
    maxutil_components = {}
    maxutil_components['total'] = []
    for uc in config["fc_unique"]: maxutil_components[uc] = []
    
    for mat_idx,mat in enumerate(matrix_list): 
        logsums.append(zeros(matrix_list[mat_idx].shape, "float32"))
        maxutil_components['total'].append(zeros(matrix_list[mat_idx].shape, "float32"))
        for uc in config["fc_unique"]: maxutil_components[uc].append(zeros(matrix_list[mat_idx].shape, "float32"))

    for source, the_target in iter(work_queue.get, 'STOP'):
        idx = idx + 1
        logging.info("Idx %d  source zone %d : Selecting random sample of generated paths..." % (idx, source))
        
        if source in the_target:
            del the_target[source]
        
        master_sets = {}
        for t in the_target:  # master_sets = { targetzone1:[] targetzone2:[] targetzone3:[] ... }
            master_sets[t] = []
        to_iter = 1
        if master_config.choice_set_config['randomize_after']:
            to_iter = master_config.choice_set_config['randomize_after_iters']
        while to_iter:
            to_iter = to_iter - 1
            for fname in glob.glob(os.path.join(master_config.assign_config['pickle_path'], str(source) + '_*')):
                f = open(fname, 'rb')
                target_paths = cPickle.load(f)  # target_paths = { targetzone1:[path] targetzone2:[path] ...} where path=[sourcezone, (sourcezone,B1), (A2,B2),...,(An,targetzone),targetzone]
                f.close()
                for t in the_target:
                    if t in target_paths:
                        master_sets[t].append(target_paths[t]) # master_sets = { targetzone1:[path1,path2,path3,...]. if to_iter=3, the path list occurs 3 times
        
        filtered_sets = {}
        for t in master_sets:
            if master_sets[t] != []:
                #filter master set
                # logging.info("filtering set for origin %4d destination %4d" % (source, t))
                filtered_sets[t] = ds.filter_master(this_network, None, master_sets[t], master_config.choice_set_config)
            
        (retlogsums,retmaxutils,retmaxutilcomponents) = trace_and_load(this_network, filtered_sets, master_config, matrix_list, source)
        
        # incorporate these logs sums
        for mat_idx in range(len(matrix_list)): 
            logsums[mat_idx][source-1,:] += retlogsums[mat_idx]
            maxutil_components['total'][mat_idx][source-1,:] += retmaxutils[mat_idx]
            for uc in config["fc_unique"]: 
                maxutil_components[uc][mat_idx][source-1,:] += retmaxutilcomponents[uc][mat_idx]

    
    done_queue.put((this_network.orig_network,logsums,maxutil_components))
    done_queue.put('STOP')
    logging.info("Finished inverted_assignment_load_worker.")
    return True

if __name__ == '__main__':
    
    parser = OptionParser()
    parser.add_option("-m", dest="master_config", help="python path to master configuration module")
    parser.add_option("-c", "--choice_set_gen", dest="choice_set_gen", default=False,
                      action="store_true")
    parser.add_option("-l", "--logsum_gen", dest="logsum_gen", default=False,
                      action="store_true")
    
    (options, args) = parser.parse_args()
    
    mandatory = ['master_config']
    for m in mandatory:
        if not options.__dict__[m]:
            parser.print_help()
            sys.exit()

    #set up
    master_config = rm_misc.get_class_instance_from_python_path(options.master_config)
    
    if options.choice_set_gen:  logfile = "choice_set_gen.log"
    elif options.logsum_gen:    logfile = "logsum_gen.log"
    else:                       logfile = "bike_assign.log"
    logfile = os.path.join(master_config.output_config['output_dir'], logfile)
    
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        filename=logfile,
                        filemode='a')
    
    logging.info('==============================================================================')
    logging.info('Starting with %d processes' % (master_config['n_processes']))

    # Read trip table matrices only if we're doing assignment
    matrix_list = []
    if not options.choice_set_gen and not options.logsum_gen:
        logging.info("Reading matrices...")
        for filename in master_config.assign_config['matrix_filenames']:
            matrix_list.append(rm_input.read_matrix(filename, headerline=False))
        logging.info("Done")
    else:
        matrix_list.append(ones((master_config.assign_config['max_inner'], master_config.assign_config['max_inner']), int))
    
    # mkdir / delete old path files if we're generating new ones
    if options.choice_set_gen or not master_config.assign_config['load_paths_from_files']:
        if os.path.exists(master_config.assign_config['pickle_path']):
            logging.info("Deleting old path files...")
            for f in glob.glob(os.path.join(master_config.assign_config['pickle_path'], '*')):
                os.remove(f)
            logging.info("Done.")
        else:
            os.mkdir(master_config.assign_config['pickle_path'])
        
    
    #project outer trips
    logging.info("Reading outer network...")
    outer_network = TransportNetwork(master_config.outer_network_config)
    logging.info("Done.")
    
    logging.info("Projecting outer trips... ")
    for mat_idx,mat in enumerate(matrix_list):
        matrix_list[mat_idx] = project_outer_trips(outer_network, mat, master_config.assign_config)
    del outer_network
    logging.info("Done.")
    
    logging.info("Setting up inner network...")
    prelim_network = TransportNetwork(master_config.network_config)
    for e in prelim_network.edges_iter(data=True):
        for load_name in master_config.assign_config['load_names']:
            e[2][load_name] = 0
    
    #exclude links
    if 'exclude_group' in master_config.network_config:
        for variable in master_config.network_config['exclude_group']:
            exclude = prelim_network.select_edges_where(variable, master_config.network_config['exclude_group'][variable][0], master_config.network_config['exclude_group'][variable][1], False)
            prelim_network.remove_edges_from(exclude)
    
    #create pseudo_dual
    network = prelim_network
    if 'use_dual' in master_config.network_config:
        if master_config.network_config['use_dual']:
            network = create_pseudo_dual(prelim_network)
            network.make_centroid_gateways()
    logging.info("Done.")
    
    #read ds coefficient bounding box
    ext_bound, master_config.choice_set_config['weights'], master_config.choice_set_config['ranges'] = rm_input.read_bound(master_config.assign_config['bound_file'], return_ranges=True)
    del_keys = []
    if master_config.choice_set_config['bound_file_override'] == True:
        master_config.choice_set_config['variables'] = ext_bound.keys()
    else:
        for key in ext_bound:
            if key not in master_config.choice_set_config['variables']:
                del_keys.append(key)
        for key in del_keys:
            del ext_bound[key]
    logging.debug("ext_bound=" + str(ext_bound))
    
    #time-dependent variables not supported for assignment
    if master_config.choice_set_config['method'] == 'doubly_stochastic':
        for var in master_config.choice_set_config['variables']:
            if var in master_config['time_dependent_relation'] :
                raise Exception, 'Time-dependent variables not supported for assignment'
    
    if master_config.assign_config['test_small_matrix']:
        from_range = range(4)
    else:
        from_range = range(master_config.assign_config['max_inner'])
    to_range = range(master_config.assign_config['max_inner'])

    if 'skip_zones' in master_config.assign_config:
        for skipzone in master_config.assign_config['skip_zones']:
            try:
                from_range.remove(skipzone - 1)
            except:
                logging.debug("Processing 'skip_zones', removing %d from from_range:" % (skipzone))
                logging.debug(sys.exc_info()[0])
            try:
                to_range.remove(skipzone - 1)
            except:
                logging.debug("Processing 'skip_zones', removing %d from to_range:" % (skipzone))
                logging.debug(sys.exc_info()[0])
    logging.debug("from_range=" + str(from_range))

    # inverted optimization
    if master_config.choice_set_config['inverted'] and master_config.choice_set_config['method'] == 'doubly_stochastic':
        
        #perform initial searches
        work_queue = Queue()
        done_queue = Queue()
        processes = []

        # st_dict = source target dictionary
        # e.g. { source_taz => { target1:1, target2:1, target3:1, ... }
        st_dict = {}
        for i in from_range:
            the_target = {}
            for j in to_range:
                for mat in matrix_list:
                    if mat[i,j]>0 and i!=j: the_target[j + 1] = 1
                    # do it for all, regardless of trips
                    # if i != j: the_target[j + 1] = 1
            st_dict[i + 1] = the_target
        
        logging.info("inverted_N_attr=%d, inverted_N_param=%d inverted_multiple=%d" % 
                     (master_config.choice_set_config['inverted_N_attr'],
                      master_config.choice_set_config['inverted_N_param'],
                      master_config.choice_set_config['inverted_multiple']))
                
        num_link_seeds = int(master_config.choice_set_config['inverted_N_attr'] * 
                            master_config.choice_set_config['inverted_multiple'])
        samp_size = (master_config.choice_set_config['inverted_N_attr'] * 
                         master_config.choice_set_config['inverted_N_param'])
        num_full_seeds = int(samp_size * master_config.choice_set_config['inverted_multiple'])


        logging.debug("num_link_seeds=%d samp_size=%d num_full_seeds=%d" % 
                      (num_link_seeds, samp_size, num_full_seeds))

        # makes a list of samp_size 1's and then pads it out with zeros so the total len is
        # num_full_seeds = samp_size * 'inverted_multiple'
        # e.g. if 'inverted_multiple' is 2, then half are zeros
        select_from = [1] * samp_size + [0] * (num_full_seeds - samp_size)
        
        # for each source, shuffle the select_from list and keep a copy in seed_selections
        seed_selections = {}
        for source in st_dict:
            random.shuffle(select_from)
            seed_selections[source] = list(select_from)
        # logging.debug("seed_selections="+str(seed_selections))
        
        if options.choice_set_gen or not master_config.assign_config['load_paths_from_files']:
        
            # the work_queue contains items 0,...,num_link_seeds-1, or 0,..,N_attr*multiple
            for i in range(num_link_seeds):
                work_queue.put(i)
        
            for w in xrange(master_config['n_processes']):
                p = Process(target=inverted_assignment_search_worker,
                            args=(work_queue, done_queue, network, master_config, ext_bound,
                                  st_dict, seed_selections))
                logging.info("Spawning subprocess " + str(p))
                p.start()
                processes.append(p)
                work_queue.put('STOP')

            for p in processes:
                logging.debug("calling p.join on %s" % (p.name))
                p.join(60 * 60 * 3) # 3 hour timeout
                logging.info("Subprocess %s returned with exitcode %d" % (p.name, p.exitcode))
        
            result = []
            for i in range(master_config['n_processes']):
                result = result + list(iter(done_queue.get, 'STOP'))
                logging.debug("i=%d result=%s" % (i, str(result)))
            del result
        
        # we're not doing assignment yet, we're done
        if options.choice_set_gen:
            logging.info("Done with choice set generation. Exiting.")
            exit(0)
            
        #load network
        work_queue = Queue()
        done_queue = Queue()
        processes = []
        
        for source in st_dict:
            work_queue.put((source, st_dict[source]))
            
        for w in xrange(master_config['n_processes']):
            p = Process(target=inverted_assignment_load_worker,
                        args=(work_queue, done_queue, network, master_config, ext_bound, matrix_list))
            p.start()
            processes.append(p)
            work_queue.put('STOP')
    
    # noninverted version
    else:
        #perform initial searches
        logging.info("Creating child processes...")
        work_queue = Queue()
        done_queue = Queue()
        processes = []
        
        for i in from_range:
            the_target = {}
            for j in to_range:
                for mat in matrix_list:
                    if mat[i, j] > 0 and i != j:
                        the_target[j + 1] = 1
            work_queue.put((i + 1, the_target))
        
        for w in xrange(master_config['n_processes']):
            p = Process(target=assign_worker, args=(work_queue, done_queue, network, master_config, ext_bound, matrix))
            p.start()
            processes.append(p)
            work_queue.put('STOP')

    #combine loads from different processes
    net_list = []
    for i in range(master_config['n_processes']):
        net_list = net_list + list(iter(done_queue.get, 'STOP'))
            
    for p in processes:
        p.join()
    
    if master_config.assign_config['delete_paths']:
        for f in glob.glob(os.path.join(master_config.assign_config['pickle_path'], '*')):
            os.remove(f)

    logging.info("Combining loads...")
    
    list_and_logsums = net_list.pop()
    
    final_net = list_and_logsums[0]
    final_logsums = list_and_logsums[1]
    final_maxutil_components = list_and_logsums[2]

    for net_list_idx in range(len(net_list)):       
        for mat_idx in range(len(matrix_list)):
        
            # add up the networks
            for e in final_net.edges_iter(data=True):
                final_net[e[0]][e[1]][master_config.assign_config['load_names'][mat_idx]] \
                     = final_net[e[0]][e[1]][master_config.assign_config['load_names'][mat_idx]] \
                    + net_list[net_list_idx][0][e[0]][e[1]][master_config.assign_config['load_names'][mat_idx]]
    
            # add up the logsums and maxutils
            final_logsums[mat_idx] += net_list[net_list_idx][1][mat_idx]
            final_maxutil_components['total'][mat_idx] += net_list[net_list_idx][2]['total'][mat_idx]
            
            for uc in master_config.assign_config['fc_unique']:
                final_maxutil_components[uc][mat_idx] += net_list[net_list_idx][2][uc][mat_idx]

    # intrazonals
    alltazs = set(from_range) | set(to_range)
    for taz in alltazs:
        # max of the logsum from all origins
        maxOriginLogsum = -9999
        for origin in from_range:
            if final_logsums[0][origin-1,taz-1]==0: continue  # inaccessible
            maxOriginLogsum = max(maxOriginLogsum, final_logsums[0][origin-1,taz-1])
            
        maxDestinationLogsum = -9999
        for destination in to_range:
            if final_logsums[0][taz-1,destination-1]==0: continue  # inaccessible
            maxDestinationLogsum = max(maxDestinationLogsum, final_logsums[0][taz-1,destination-1])
        final_logsums[0][taz-1,taz-1] = 0.5*(maxOriginLogsum+maxDestinationLogsum)
        
    logging.info("Writing output file...")
    
    
    if 'assign' in master_config.output_config['output_type'] and not options.logsum_gen:
    
        # put the assign file in the output_dir            
        master_config.output_config['assign_data'] = \
          os.path.join(master_config.output_config['output_dir'],
                       master_config.output_config['filename_dict']['assign_data'])
        
        rm_output.create_csv_from_assignment(final_net, master_config)

    if options.logsum_gen and 'logsum' in master_config.output_config['output_type']:
        master_config.output_config['logsum_data'] = \
          os.path.join(master_config.output_config['output_dir'],
                       master_config.output_config['filename_dict']['logsum_data'])
        master_config.output_config['maxutil_data'] = \
          os.path.join(master_config.output_config['output_dir'],
                       master_config.output_config['filename_dict']['maxutil_data'])             
        rm_output.create_h5_from_logsums(final_logsums[0], final_maxutil_components, master_config)
        
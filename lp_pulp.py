from numpy import array
from pulp import (
    GUROBI_CMD,
    PULP_CBC_CMD,
    LpMinimize,
    LpProblem,
    LpStatus,
    LpVariable,
    lpSum,
    value,
)
#from hashlib import new
#from itertools import *
import networkx as nx

def lp_energy(N, H, K, c, p, c_tilde, p_tilde, mc, env, Tmax, solver, verbose):

    x = LpVariable.dicts("x_", (H, N), 0, cat="CONTINUOUS")  # dimension nxh
    y = LpVariable.dicts("y_", (H, K), 0, cat="CONTINUOUS")  # e in the LP, dimension kxh

    prob = LpProblem("myProblem", LpMinimize)

    # 3
    for i in N:
        prob.addConstraint(lpSum([x[h][i] for h in H]) >= 1)

    # 4
    for h in H:
        prob.addConstraint(
            (
                lpSum([p[h][i] * x[h][i] for i in N])
                + lpSum([p_tilde[h][k] * y[h][k] for k in K])
            )
            <= mc[h] * Tmax
        )

    # 5
    for h in H:
        for k in K:
            task_per_env = [i_env for i_env in N if env[i_env] == k]
            if len(task_per_env) != 0:
                prob.addConstraint(
                    (
                        lpSum([p[h][i] * x[h][i] for i in task_per_env])
                        - y[h][k] * (Tmax - p_tilde[h][k])
                    )
                    <= 0
                )

    prob += lpSum([c[h][i] * x[h][i] for i in N] for h in H) + lpSum(
        [c_tilde[h][k] * y[h][k] for k in K] for h in H
    )

    solution_x = [[0 for col in H] for row in N]
    solution_y = [[0 for col in H] for row in K]

    if solver == "CBC":
        if verbose == 1:
            status = prob.solve(PULP_CBC_CMD())
        else:
            status = prob.solve(PULP_CBC_CMD(msg=0))
    else:
        if verbose == 1:
            status = prob.solve(GUROBI_CMD())
        else:
            status = prob.solve(GUROBI_CMD(msg=0))

    print(LpStatus[status])
    print("Value ", value(prob.objective))
    print("Status: ", status)
    # print(prob.constraints())

    for v in prob.variables():
        solution_var = v.name.split("_")[0]
        index_i = int(v.name.split("_")[-1])
        index_j = int(v.name.split("_")[-2])

        if solution_var == "x":
            solution_x[index_i][index_j] = v.varValue
        else:
            solution_y[index_i][index_j] = v.varValue

    solution_x = array(solution_x)
    solution_y = array(solution_y)

    return solution_x, solution_y


def compute_max_cmax_and_tmax(c, p, b, d, K, M, N):
    """
    Compute the max Cmax and Tmax allowed. Requirement: c and p, and b and d should have the same dimension, then:
    if we place all jobs and environments on one machine, 
    get the total cost on the worst machine, 
    and the total time on the worst machine.
    The worst cost and the worst time might not be on the same machine.
    """
    cmax = 0
    tmax = 0
    
    for i in range(0, M):
        curr_cost = sum(d[i]) + sum(c[i])
        if curr_cost > cmax:
            cmax = curr_cost
        curr_time = sum(b[i]) + sum(p[i])
        if curr_time > tmax:
            tmax = curr_time
    return cmax, tmax

def get_solution_cost(x, e, M, N, K, c, p, d, b):
    
    return int(np.sum(x * c) + np.sum(e * d))

def get_solution_makespan(x, e, M, N, K, c, p, d, b):
    x_time = x * p
    e_time = e * b

    return int(max([np.sum(x_time[m]) + np.sum(e_time[m]) for m in range(M)]))

def find_Tmin(Cmax, Tmax, M, N, K, c, p, d, b, env):#, factor):

    low_tmax = 0
    high_tmax = Tmax
    mid_tmax = 0

    iterations = 0

    while (low_tmax + 1 < high_tmax and iterations < 2):
        mid_tmax = round((high_tmax + low_tmax) / 2, 2)
        status_tmax, x_new, e_new = LP(Cmax, mid_tmax, M, N, K, c, p, d, b, env)
        
        # If x is greater, ignore left half
        if status_tmax == 0:
            high_tmax = mid_tmax

        # No solution, revert to previous solution
        else:
            low_tmax = mid_tmax
        
        iterations += 1
    
    return high_tmax

def to_integer_solution(x, M, N, K, c, p, d, b, env):

    #try:
        
    #if the solution given is already integer, assign the environments correctly and return
    if np.all([[not (j%1) for j in i]for i in x]):
        e = np.zeros((M, K))
        for m in range(M):
            for t in range(N):
                if x[m][t] == 1 and e[m][env[t]] == 0:
                    e[m][env[t]] = 1
        return True, x, e

    #k is a list of the number of sub-machines for each machine
    #k_inv if we align every sub-machine, k_inv gives us for each sub-machine to what machine it correspond
    k = []
    k_inv = []
    count = 0
    for i in range(M):
        k.append(int(np.ceil(np.sum(x[i]))))
        for j in range(k[i]):
            k_inv.append(count)  
        count = count + 1

    #number of sub-machines
    subM = int(np.sum(k))

    #
    bip = np.zeros((subM, N))

    #networkx bipartite graph
    B = nx.Graph()
    B.add_nodes_from(range(subM), bipartite=0)
    B.add_nodes_from(range(subM, subM + N), bipartite=1)

    #pour chaque machine
    for i in range(M):
        #subi the index of the 1st sub-machine of machine i
        subi = int(sum(k[:i]))
        #we order the tasks for machine i by decreasing processing times
        ordered_pi = sorted([[(p[i][j]+b[i][env[j]])*np.ceil(x[i][j]), j] for j in range(N)], reverse=True, key=lambda x: x[0])

        #take the first task
        count = 0
        e = ordered_pi[count]
        
        offset = 0

        #setting up the edges of the bipartite graph, like in 1st figure of page 16
        while count <= len(ordered_pi)-1 and ordered_pi[count][0] != 0:
            e = ordered_pi[count]
            filler = 0
            if np.sum(bip[subi + offset]) + x[i][e[1]] >= 1:
                filler = 1 - np.sum(bip[subi + offset])
                bip[subi + offset][e[1]] = filler
                B.add_edge(subi + offset, subM + e[1], weight = x[i][e[1]])
                offset = offset + 1
            
            if x[i][e[1]] - filler > 0.001:
                bip[subi + offset][e[1]] = bip[subi + offset][e[1]] + x[i][e[1]] - filler
                B.add_edge(subi + offset, subM + e[1], weight = x[i][e[1]])
            
            count = count + 1

    #cleaning the edges that are too small due to numerical errors, and the nodes that are not connected
    to_remove = [(a,b) for a, b, attrs in B.edges(data=True) if attrs["weight"] <= 0.00001]
    B.remove_edges_from(to_remove)
    B.remove_nodes_from(list(nx.isolates(B)))

    top_nodes = {n for n, d in B.nodes(data=True) if d["bipartite"] == 1}

    #minimum weight full matching, see figure 2 of page 16
    match = nx.algorithms.bipartite.matching.minimum_weight_full_matching(B, top_nodes)

    #formating the solution
    out = np.zeros((M, N))
    out_e = np.zeros((M, K))
    
    for i, m in enumerate(k_inv):
        try:
            t = match[i] - subM
            out[m][t] = 1
            if out_e[m][env[t]] == 0:
                out_e[m][env[t]] = 1
        except:
            pass
    
    return True, out, out_e
    """
    except:
        #return 1, 1
        return False, 0, 0
    """

def minimize_cmax_and_tmax(Cmax, Tmax, M, N, K, c, p, d, b, env, mc):#, factor):
    # Initialization
    new_cost = Cmax
    new_makespan = Tmax
    
    list_of_solution = []
    list_of_cmax_used = []
    list_of_tmax_used = []

    list_of_cmax_lp = []
    list_of_tmax_lp = []

    list_of_valid_cmax = []
    list_of_valid_tmax = []

    # Compute intial solution with the initial Cmax and Tmax
    
    status_tmax, x_new, e_new = LP(Cmax, Tmax, M, N, K, c, p, d, b, env, mc)
    list_of_cmax_used.append(Cmax)
    list_of_tmax_used.append(Tmax)

    
    status_valid, x_valid, e_valid = status_tmax, x_new, e_new
    cost_lp = get_solution_cost(x_new, e_new, M, N, K, c, p, d, b)
    makespan_lp = get_solution_makespan(x_new, e_new, M, N, K, c, p, d, b)
    list_of_cmax_lp.append(cost_lp)
    list_of_tmax_lp.append(makespan_lp)
    
    status_integral_solution, x_valid2, e_valid2 = to_integer_solution(x_new, M, N, K, c, p, d, b, env)
    new_cost = get_solution_cost(x_valid2, e_valid2, M, N, K, c, p, d, b)
    new_makespan = get_solution_makespan(x_valid2, e_valid2, M, N, K, c, p, d, b)
    list_of_valid_cmax.append(new_cost)
    list_of_valid_tmax.append(new_makespan)    
    print("Integral solution: ", x_valid2, e_valid2)

    # Save valid solutions
    list_of_solution.append([Cmax, Tmax, x_valid, e_valid])

    low_tmax = 0
    high_tmax = makespan_lp
    mid_tmax = 0
    iterations = 0

    while (low_tmax <= high_tmax and iterations < 5):
        print("LP Iteration: ", iterations)
        mid_tmax = int((high_tmax + low_tmax) / 2)
        status_tmax, x_new, e_new = LP(Cmax, mid_tmax, M, N, K, c, p, d, b, env, mc)

        if status_tmax == 1: # ==== To use the float solution
            print("Achou solução, entrou")
            list_of_cmax_used.append(Cmax)
            list_of_tmax_used.append(mid_tmax)

            high_tmax = mid_tmax
            
            cost_lp = get_solution_cost(x_new, e_new, M, N, K, c, p, d, b)
            makespan_lp = get_solution_makespan(x_new, e_new, M, N, K, c, p, d, b)
            list_of_cmax_lp.append(cost_lp)
            list_of_tmax_lp.append(makespan_lp)
                        
            status_integral_solution, x_integral_solution, e_integral_solution = to_integer_solution(x_new, M, N, K, c, p, d, b, env)
            if(status_integral_solution==True):
                x_valid2 = x_integral_solution
                e_valid2 = e_integral_solution
                print("After integral solution: ", x_valid2)
                status_valid  = status_tmax

                new_cost = get_solution_cost(x_valid2, e_valid, M, N, K, c, p, d, b)
                new_makespan = get_solution_makespan(x_valid2, e_valid, M, N, K, c, p, d, b)

                list_of_solution.append([new_cost, new_makespan, x_valid2, e_valid2])
                list_of_valid_cmax.append(new_cost)
                list_of_valid_tmax.append(new_makespan)
            else:
                print("Não converteu")
                list_of_valid_cmax.append(None)
                list_of_valid_tmax.append(None)          
        # No solution, revert to previous solution
        else:
            low_tmax = mid_tmax

        iterations += 1
        print(list_of_valid_tmax)
        print("x_valid: ", x_new)
    return status_valid, x_valid2, e_valid2, new_cost, new_makespan, list_of_valid_cmax, list_of_valid_tmax, list_of_cmax_used, list_of_tmax_used, list_of_cmax_lp, list_of_tmax_lp

def get_cost(x, e, c, d):
    tcost = np.sum(x*c)
    ecost = np.sum(e*d)
    
    return tcost + ecost
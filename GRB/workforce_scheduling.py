import gurobipy as gp
from gurobipy import GRB


import pandas as pd
from pylab import *
import matplotlib
import matplotlib.pyplot as plt

# Create initial model.
model = gp.Model("workforce5")

"""## Input Data

We define all the input data of the model.
"""

# Number of workers required for each shift.
# shifts, shiftRequirements = gp.multidict({
#   "Mon1":  3,
#   "Tue2":  2,
#   "Wed3":  4,
#   "Thu4":  4,
#   "Fri5":  5,
#   "Sat6":  6,
#   "Sun7":  5,
#   "Mon8":  2,
#   "Tue9":  2,
#   "Wed10": 3,
#   "Thu11": 4,
#   "Fri12": 6,
#   "Sat13": 7,
#   "Sun14": 5 })

shifts = ['Mon1', 'Tue2', 'Wed3', 'Thu4', 'Fri5', 'Sat6', 'Sun7', 'Mon8', 'Tue9', 'Wed10', 'Thu11', 'Fri12', 'Sat13', 'Sun14']
shiftRequirements = {
  "Mon1":  3,
  "Tue2":  2,
  "Wed3":  4,
  "Thu4":  4,
  "Fri5":  5,
  "Sat6":  6,
  "Sun7":  5,
  "Mon8":  2,
  "Tue9":  2,
  "Wed10": 3,
  "Thu11": 4,
  "Fri12": 6,
  "Sat13": 7,
  "Sun14": 5 }



# Amount each worker is paid to work one shift.
# workers, pay = gp.multidict({
#   "Amy":   10,
#   "Bob":   12,
#   "Cathy": 10,
#   "Dan":   8,
#   "Ed":    8,
#   "Fred":  9,
#   "Gu":    11 })

workers = ["Amy", "Bob", "Cathy", "Dan", "Ed", "Fred", "Gu"]
pay = {
  "Amy":   10,
  "Bob":   12,
  "Cathy": 10,
  "Dan":   8,
  "Ed":    8,
  "Fred":  9,
  "Gu":    11 } 


# Worker availability: defines on which day each employed worker is available.

availability = gp.tuplelist([
('Amy', 'Tue2'), ('Amy', 'Wed3'), ('Amy', 'Fri5'), ('Amy', 'Sun7'),
('Amy', 'Tue9'), ('Amy', 'Wed10'), ('Amy', 'Thu11'), ('Amy', 'Fri12'),
('Amy', 'Sat13'), ('Amy', 'Sun14'), ('Bob', 'Mon1'), ('Bob', 'Tue2'),
('Bob', 'Fri5'), ('Bob', 'Sat6'), ('Bob', 'Mon8'), ('Bob', 'Thu11'),
('Bob', 'Sat13'), ('Cathy', 'Wed3'), ('Cathy', 'Thu4'), ('Cathy', 'Fri5'),
('Cathy', 'Sun7'), ('Cathy', 'Mon8'), ('Cathy', 'Tue9'), ('Cathy', 'Wed10'),
('Cathy', 'Thu11'), ('Cathy', 'Fri12'), ('Cathy', 'Sat13'),
('Cathy', 'Sun14'), ('Dan', 'Tue2'), ('Dan', 'Wed3'), ('Dan', 'Fri5'),
('Dan', 'Sat6'), ('Dan', 'Mon8'), ('Dan', 'Tue9'), ('Dan', 'Wed10'),
('Dan', 'Thu11'), ('Dan', 'Fri12'), ('Dan', 'Sat13'), ('Dan', 'Sun14'),
('Ed', 'Mon1'), ('Ed', 'Tue2'), ('Ed', 'Wed3'), ('Ed', 'Thu4'),
('Ed', 'Fri5'), ('Ed', 'Sun7'), ('Ed', 'Mon8'), ('Ed', 'Tue9'),
('Ed', 'Thu11'), ('Ed', 'Sat13'), ('Ed', 'Sun14'), ('Fred', 'Mon1'),
('Fred', 'Tue2'), ('Fred', 'Wed3'), ('Fred', 'Sat6'), ('Fred', 'Mon8'),
('Fred', 'Tue9'), ('Fred', 'Fri12'), ('Fred', 'Sat13'), ('Fred', 'Sun14'),
('Gu', 'Mon1'), ('Gu', 'Tue2'), ('Gu', 'Wed3'), ('Gu', 'Fri5'),
('Gu', 'Sat6'), ('Gu', 'Sun7'), ('Gu', 'Mon8'), ('Gu', 'Tue9'),
('Gu', 'Wed10'), ('Gu', 'Thu11'), ('Gu', 'Fri12'), ('Gu', 'Sat13'),
('Gu', 'Sun14')
])

"""## Model Deployment"""


# Initialize assignment decision variables.

x = model.addVars(availability, vtype=GRB.BINARY, name="x")

# Slack decision variables determine the number of extra workers required to satisfy the requirements
# of each shift
slacks = model.addVars(shifts, name="Slack")


# Auxiliary variable totSlack to represent the total number of extra workers required to satisfy the
# requirements of all the shifts.
totSlack = model.addVar(name='totSlack')

# Auxiliary variable totShifts counts the total shifts worked by each employed worker
totShifts = model.addVars(workers, name="TotShifts")


# Constraint: All shifts requirements most be satisfied.

shift_reqmts = model.addConstrs((x.sum('*',s) + slacks[s] == shiftRequirements[s] for s in shifts), name='shiftRequirement')



# Constraint: set the auxiliary variable (totSlack) equal to the total number of extra workers
# required to satisfy shift requirements

num_temps = model.addConstr(totSlack == slacks.sum(), name='totSlack')


# Constraint: compute the total number of shifts for each worker

num_shifts = model.addConstrs((totShifts[w] == x.sum(w,'*') for w in workers), name='totShifts')



# Auxiliary variables.
# minShift is the minimum number of shifts allocated to workers
# maxShift is the maximum number of shifts allocated to workers

minShift = model.addVar(name='minShift')

maxShift = model.addVar(name='maxShift')

# Constraint:
# The addGenConstrMin() method of the model object m adds a new general constraint that
# determines the minimum value among a set of variables.
# The first argument is the variable whose value will be equal to the minimum of the other variables,
# minShift in this case.
# The second argument is the set variables over which the minimum will be taken, (totShifts) in
# this case.
# Recall that the totShifts variable is defined over the set of worker and determines the number of
# shifts that an employed worker will work. The third argument is the name of this constraint.

min_constr = model.addGenConstrMin(minShift, totShifts, name='minShift')

# Constraint:
# Similarly, the addGenConstrMax() method of the model object m adds a new general
# constraint that determines the maximum value among a set of variables.

max_constr = model.addGenConstrMax(maxShift, totShifts, name='maxShift')

"""We have a primary and a secondary objective which both aim to minimize."""

# Set global sense for ALL objectives.
# This means that all objectives of the model object m are going to be minimized
model.ModelSense = GRB.MINIMIZE


# Set up primary objective.

# The setObjectiveN() method of the model object m allows to define multiple objectives.
# The first argument is the linear expression defining the most important objective, called primary
# objective, in this case it is the minimization of extra workers required to satisfy shift
# requirements.
# The second argument is the index of the objective function, we set the index of the primary
# objective to be equal to 0.
# The third argument is the priority of the objective.
# The fourth argument is the relative tolerance to degrade this objective when a lower priority
# objective is optimized. The fifth argument is the name of this objective.
# A hierarchical or lexicographic approach assigns a priority to each objective, and optimizes
# for the objectives in decreasing priority order.
# For this problem, we have two objectives, and the primary objective has the highest priority
# which is equal to 2.
# When the secondary objective is minimized, since the relative tolerance is 0.2, we can only
# increase the minimum number of extra workers up to 20%.
# For example if the minimum number extra workers is 10, then when optimizing the secondary objective
# we can have up to 12 extra workers.

model.setObjectiveN(totSlack, index=0, priority=2, reltol=0.2, name='TotalSlack')


# Set up secondary objective.

# The secondary objective is called fairness and its goal is to balance the workload assigned
# to the employed workers.
# To balance the workload assigned to the employed workers, we can minimize the difference
# between the maximum number of shifts assigned to an employed worker and the minimum number
# of shifts assigned to an employed worker.

model.setObjectiveN(maxShift - minShift, index=1, priority=1, name='Fairness')

# # Save model formulation for inspection

# model.write('workforce.lp')

# update model
model.update()


# Optimize
# This method runs the optimization engine to solve the MIP problem in the model object m
model.optimize()

# # The Status attribute  provides current optimization status of the model object m
# # In workforce model, we check if the model is infeasible or unbounded and report this situation
# status = m.Status
# if status == GRB.Status.INF_OR_UNBD or status == GRB.Status.INFEASIBLE  or status == GRB.Status.UNBOUNDED:
#     print('The model cannot be solved because it is infeasible or unbounded')
#     sys.exit(0)
# # If the optimization status of the model is not optimal for some other reason, we report that
# # situation.
# if status != GRB.Status.OPTIMAL:
#     print('Optimization was stopped with status ' + str(status))
#     sys.exit(0)

# Print total slack and the number of shifts worked for each worker
# The KPIs for this optimization number is the number of extra worked required to satisfy
# demand and the number of shifts that each employed worker is working.
solution = {}
shifts_sol = {}
solution['Total slack required'] = str(totSlack.X)
assignments_all = {}
gant={}

assignments = dict()
for [w, s] in availability:
    if x[w, s].x == 1:
        if w in assignments:
            assignments[w].append(s)
        else:
            assignments[w] = [s]


print(pd.DataFrame.from_records(list(solution.items()), columns=['KPI', 'Value']))
print('-'*50)

for w in workers:
    shifts_sol[w]=totShifts[w].X
    assignments_all[w]=assignments.get(w, [])

print('Shifts')
print(pd.DataFrame.from_records(list(shifts_sol.items()), columns=['Worker', 'Number of shifts']))

# y_pos = np.arange(len(shifts_sol.keys()))
# plt.bar(y_pos,shifts_sol.values() , align='center')
# plt.xticks(y_pos, shifts_sol.keys())
# plt.show()

print('-'*50)
for w in assignments_all:
    gant[w] = [w]
    for d in shifts:
        gant[w].append('*' if d in assignments_all[w] else '-')

print('Assigments')
print('Symbols: \'-\': not working, \'*\': working')
pd.set_option('display.width', 1000)
print(pd.DataFrame.from_records(list(gant.values()), columns=['worker']+shifts))



# OptiChat metadata - REQUIRED for Gurobi models
# This metadata helps OptiChat understand your model structure
model._optichat_metadata = {
    'sets': {
        'shifts': {
            'description': 'Set of shifts over a two-week planning horizon',
            'elements': shifts
        },
        'workers': {
            'description': 'Set of employed workers',
            'elements': workers
        },
        'availability': {
            'description': 'Worker-shift pairs where worker is available',
            'elements': list(availability)
        }
    },
    'parameters': {
        'shiftRequirements': {
            'description': 'Number of workers required for each shift',
            'is_indexed': True,
            'index_set': shifts,
            'is_RHS': True,
            'is_mutable': True,
            'cons_in': ['shiftRequirement']
        },
        'pay': {
            'description': 'Salary per day for each worker',
            'is_indexed': True,
            'index_set': workers,
            'is_RHS': False,  # Not used in constraints in this model
            'is_mutable': True,
            'cons_in': []
        }
    },
    'variables': {
        'x': {
            'description': 'Binary assignment of workers to shifts (1 if assigned, 0 otherwise)'
        },
        'slacks': {
            'description': 'Number of extra (temp) workers required for each shift'
        },
        'totSlack': {
            'description': 'Total number of extra workers required across all shifts'
        },
        'totShifts': {
            'description': 'Total number of shifts worked by each employed worker'
        },
        'minShift': {
            'description': 'Minimum number of shifts allocated to any worker'
        },
        'maxShift': {
            'description': 'Maximum number of shifts allocated to any worker'
        }
    },
    'constraints': {
        'shiftRequirement': {
            'description': 'Ensure all shift requirements are satisfied by employed workers plus temp workers',
            'params_in': {'shiftRequirements'}
        },
        'totSlack': {
            'description': 'Calculate total number of extra workers needed',
            'params_in': set()
        },
        'totShifts': {
            'description': 'Calculate total shifts worked by each employed worker',
            'params_in': set()
        },
        'minShift': {
            'description': 'General constraint to determine minimum shifts among all workers',
            'params_in': set()
        },
        'maxShift': {
            'description': 'General constraint to determine maximum shifts among all workers',
            'params_in': set()
        }
    },
    'objective': {
        'name': 'multi_objective',
        'description': 'Primary: minimize total temp workers needed; Secondary: balance workload (minimize max-min shifts)'
    }
}
"""
Simple Gurobi model example for OptiChat.

This is a basic production planning problem:
- Minimize production costs
- Subject to demand constraints
- With production capacity limits
"""

import gurobipy as gp
from gurobipy import GRB

# Create model
model = gp.Model("production_planning")

# Data
products = ['A', 'B', 'C']
demand = {'A': 100, 'B': 150, 'C': 80}
capacity = {'A': 120, 'B': 200, 'C': 100}
cost = {'A': 10, 'B': 15, 'C': 12}

# Decision variables
production = {}
for p in products:
    production[p] = model.addVar(name=f'production[{p}]', lb=0, vtype=GRB.CONTINUOUS)

# Objective: minimize total cost
model.setObjective(
    gp.quicksum(cost[p] * production[p] for p in products),
    GRB.MINIMIZE
)

# Constraints
demand_constrs = {}
capacity_constrs = {}

for p in products:
    # Demand constraint
    demand_constrs[p] = model.addConstr(
        production[p] >= demand[p],
        name=f'demand[{p}]'
    )
    
    # Capacity constraint
    capacity_constrs[p] = model.addConstr(
        production[p] <= capacity[p],
        name=f'capacity[{p}]'
    )

# Update model
model.update()

# model.optimize()

# # display optimal values of decision variables

# for p in products:
#     print(f"Produce {production[p].x:.2f} units of product {p}")

# OptiChat metadata - REQUIRED for Gurobi models
# This metadata helps OptiChat understand your model structure
model._optichat_metadata = {
    'sets': {
        'products': {
            'description': 'Set of products to manufacture',
            'elements': products
        }
    },
    'parameters': {
        'demand': {
            'description': 'Demand for each product',
            'is_indexed': True,
            'index_set': products,
            'is_RHS': True,
            'is_mutable': True,
            'cons_in': ['demand']
        },
        'capacity': {
            'description': 'Production capacity for each product',
            'is_indexed': True,
            'index_set': products,
            'is_RHS': True,
            'is_mutable': True,
            'cons_in': ['capacity']
        },
        'cost': {
            'description': 'Production cost per unit for each product',
            'is_indexed': True,
            'index_set': products,
            'is_RHS': False,  # LHS parameter (coefficient)
            'is_mutable': True,
            'cons_in': []  # In objective, not constraints
        }
    },
    'variables': {
        'production': {
            'description': 'Amount to produce for each product'
        }
    },
    'constraints': {
        'demand': {
            'description': 'Ensure production meets demand',
            'params_in': {'demand'}
        },
        'capacity': {
            'description': 'Ensure production does not exceed capacity',
            'params_in': {'capacity'}
        }
    },
    'objective': {
        'name': 'total_cost',
        'description': 'Minimize total production cost'
    }
}

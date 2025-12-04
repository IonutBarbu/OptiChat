# Gurobi Support in OptiChat

## Overview

OptiChat now supports both **Pyomo** and **Gurobipy** optimization models. The system automatically detects which framework your model uses and provides appropriate functionality.

## Model Detection

The framework is automatically detected by analyzing import statements in your code:
- `import gurobipy` or `from gurobipy` → Gurobi model
- `import pyomo` or `from pyomo` → Pyomo model

## Gurobi Model Requirements

### 1. Model Variable Name

Your model must be assigned to a variable named `model`:

```python
import gurobipy as gp
from gurobipy import GRB

model = gp.Model("my_model_name")
# ... rest of your model
```

### 2. OptiChat Metadata (Required)

For Gurobi models to work properly with OptiChat's internal tools, you **must** include metadata as a dictionary attribute on your model. This metadata describes the structure of your model.

Add this at the end of your model file:

```python
model._optichat_metadata = {
    'sets': {
        'set_name': {
            'description': 'Description of the set',
            'elements': [list of elements]
        }
    },
    'parameters': {
        'param_name': {
            'description': 'Description of the parameter',
            'is_indexed': True/False,
            'index_set': [list of indices] or None,
            'is_RHS': True/False,  # True if on right-hand side of constraints
            'is_mutable': True,
            'cons_in': ['constraint1', 'constraint2']  # List of constraints using this parameter
        }
    },
    'variables': {
        'var_name': {
            'description': 'Description of the variable'
        }
    },
    'constraints': {
        'constr_name': {
            'description': 'Description of the constraint',
            'params_in': {'param1', 'param2'}  # Set of parameters in this constraint
        }
    },
    'objective': {
        'name': 'objective_name',
        'description': 'Description of the objective function'
    }
}
```

### 3. Naming Conventions

Use consistent naming with indices in square brackets:

```python
# Good: Using index notation in variable/constraint names
production[A] = model.addVar(name='production[A]')
demand[A] = model.addConstr(production[A] >= 100, name='demand[A]')

# Not recommended: Without index notation
production_A = model.addVar(name='production_A')
demand_A = model.addConstr(production_A >= 100, name='demand_A')
```

## Complete Example

See `examples/simple_gurobi_model.py` for a complete working example with proper metadata.

```python
import gurobipy as gp
from gurobipy import GRB

# Create model
model = gp.Model("production")

# Data
products = ['A', 'B', 'C']
demand = {'A': 100, 'B': 150, 'C': 80}

# Variables
production = {}
for p in products:
    production[p] = model.addVar(name=f'production[{p}]', lb=0)

# Objective
model.setObjective(
    gp.quicksum(10 * production[p] for p in products),
    GRB.MINIMIZE
)

# Constraints
for p in products:
    model.addConstr(production[p] >= demand[p], name=f'demand[{p}]')

model.update()

# OptiChat metadata (REQUIRED)
model._optichat_metadata = {
    'sets': {
        'products': {
            'description': 'Set of products',
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
        }
    },
    'variables': {
        'production': {
            'description': 'Production quantity for each product'
        }
    },
    'constraints': {
        'demand': {
            'description': 'Meet demand for each product',
            'params_in': {'demand'}
        }
    },
    'objective': {
        'name': 'total_cost',
        'description': 'Minimize total production cost'
    }
}
```

## Metadata Field Descriptions

### Sets
- **description**: Plain English description of what the set represents
- **elements**: List of actual elements in the set

### Parameters
- **description**: What this parameter represents
- **is_indexed**: Boolean indicating if parameter has indices
- **index_set**: List of indices (or None if not indexed)
- **is_RHS**: Boolean - True if parameter appears on right-hand side of constraints (e.g., demand values), False if it's a coefficient on the left-hand side (e.g., cost coefficients)
- **is_mutable**: Boolean - typically True for parameters that might change
- **cons_in**: List of constraint names that use this parameter

### Variables
- **description**: What this decision variable represents

### Constraints
- **description**: What this constraint enforces
- **params_in**: Set of parameter names that appear in this constraint

### Objective
- **name**: Name for the objective function
- **description**: What the objective optimizes for

## Supported Features

All OptiChat features work with Gurobi models:

1. **Model Interpretation**: Automatic description of model components
2. **Feasibility Restoration**: Identify minimal changes to restore feasibility
3. **Sensitivity Analysis**: Analyze impact of parameter changes (LP models only)
4. **Component Retrieval**: Query variable values and constraint expressions
5. **Modification Evaluation**: Test what-if scenarios

## Known Limitations

1. **Metadata Required**: Unlike Pyomo models where metadata is embedded in the model structure, Gurobi models require explicit metadata
2. **LP Only for Sensitivity**: Sensitivity analysis only works for linear programs, not for MIP/MIQP
3. **Index Parsing**: Complex index structures may require careful naming conventions

## Migration from Pyomo

If you have an existing Pyomo model and want to use Gurobi:

1. Rewrite the model in Gurobi syntax
2. Add the `_optichat_metadata` dictionary
3. Use index notation in names: `var[i,j]` instead of `var_i_j`
4. Upload to OptiChat - it will automatically detect the framework

## Troubleshooting

**Issue**: Model not detected as Gurobi
- **Solution**: Ensure you have `import gurobipy` at the top of your file

**Issue**: Internal tools not working
- **Solution**: Check that `_optichat_metadata` dictionary is complete and correctly formatted

**Issue**: Variables/constraints not found
- **Solution**: Use consistent naming with square bracket indices: `name[index]`

**Issue**: Sensitivity analysis fails
- **Solution**: Ensure your model is LP (not MIP) and has been solved to optimality

## Support

For questions or issues with Gurobi support:
1. Check that your metadata follows the format in the example
2. Verify naming conventions match the pattern: `component[index]`
3. Ensure the model variable is named `model`

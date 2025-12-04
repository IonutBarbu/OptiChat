# Gurobi Support Implementation Summary

## Overview
This implementation adds native Gurobipy support to OptiChat through an abstraction layer architecture, allowing users to upload and interact with optimization models written in either Pyomo or Gurobipy while maintaining all existing functionality.

## Implementation Details

### 1. Abstraction Layer (`model_adapter.py`)
Created a unified interface for optimization models:

- **`AbstractOptimizationModel`**: Base class defining common interface
  - `solve()`: Solve the optimization model
  - `to_json()`: Convert model to JSON representation
  - `extract_iis()`: Extract IIS for infeasible models
  - `clone()`: Create a deep copy of the model
  - `get_model_type()`: Return framework type

- **`PyomoAdapter`**: Wraps existing Pyomo functionality
  - Delegates to existing `pyomo2json()` function
  - Uses Pyomo's IIS extraction

- **`GurobiAdapter`**: Implements Gurobi-specific functionality
  - Maps Gurobi status codes to Pyomo-like termination conditions
  - Implements Gurobi IIS computation
  - Delegates to new `gurobi2json()` function

- **`create_adapter()`**: Factory function to instantiate appropriate adapter

### 2. Model Type Detection (`extractor.py`)

**`detect_model_framework(code: str) -> str`**
- Analyzes import statements in the code
- Returns 'pyomo' or 'gurobi'
- Handles edge cases where both frameworks are imported

**Updated `initial_loading()`**
- Calls `detect_model_framework()` to identify the framework
- Creates appropriate adapter using `create_adapter()`
- Uses adapter's `solve()` and `to_json()` methods
- Stores `model_framework` in models_dict

### 3. Gurobi to JSON Converter (`extractor.py`)

**`gurobi2json(model, termination_condition) -> dict`**
Converts Gurobipy models to OptiChat's internal JSON representation:

- **Variables**: Extracts via `model.getVars()`, groups by base name, handles indexing
- **Constraints**: Extracts via `model.getConstrs()`, groups by base name, extracts variable usage
- **Objective**: Extracts via `model.getObjective()`
- **Metadata**: Reads from `model._optichat_metadata` dictionary for sets, parameters, descriptions
- **Model Type**: Detects LP vs IP based on variable types

### 4. Gurobi Internal Tools (`internal_tools.py`)

Implemented Gurobi-specific versions of all internal tools:

**`feasibility_restoration_gurobi()`**
- Creates model copy using `model.copy()`
- Computes IIS using `model.computeIIS()`
- Adds slack variables to IIS constraints
- Reconstructs constraints with slacks
- Minimizes sum of slacks

**`sensitivity_analysis_gurobi()`**
- Accesses dual values via `constr.Pi`
- Requires LP models (not MIP)
- Identifies constraints containing queried parameters
- Computes sensitivity based on dual values

**`components_retrival_gurobi()`**
- Retrieves variable values via `var.X`
- Retrieves constraint expressions via `model.getRow()`
- Handles variables, constraints, parameters, and objective

**`evaluate_modification_gurobi()`**
- Creates model copy
- Fixes variables to new values by setting LB=UB
- Updates constraint RHS for parameter changes
- Re-optimizes and reports results

**`dispatch_internal_tool()`**
- Routes tool calls to appropriate implementation based on `model_framework`
- Provides unified interface for both frameworks

### 5. Updated Prompts (`prompts.py`)

**Model Interpretation Prompt**
- Changed "Pyomo" to "Pyomo or Gurobipy"

**Programmer Prompt**
- Added Gurobi code examples alongside Pyomo examples
- Shows standard Gurobi solving pattern:
  ```python
  model.Params.TimeLimit = 300
  model.optimize()
  if model.status == GRB.OPTIMAL:
      print(model.ObjVal)
  ```
- Instructs to check framework and write appropriate code

**Evaluator Prompt**
- Updated to handle "Pyomo or Gurobipy code"

### 6. UI Updates (`app.py`)

**File Uploader**
- Changed label from "Load Pyomo File" to "Load Optimization Model"
- Updated help text to mention both frameworks

**Process Function**
- Detects model framework from `models_dict`
- Displays "I have uploaded a [Pyomo/Gurobipy] model"
- Updates all chat history references accordingly

**Load JSON Function**
- Similar framework detection and display updates

### 7. Documentation

**`GUROBI_SUPPORT.md`**
Comprehensive guide covering:
- Model detection mechanism
- Metadata requirements and format
- Complete example with metadata
- Field-by-field metadata descriptions
- Supported features
- Known limitations
- Migration guide from Pyomo
- Troubleshooting section

**`examples/simple_gurobi_model.py`**
- Complete working example of a Gurobi model
- Production planning problem
- Properly formatted metadata
- Commented to explain requirements

**Updated `README.md`**
- Added Gurobi support to overview
- Updated installation instructions
- Added Gurobi Support section with quick start
- Links to detailed documentation

## Key Design Decisions

### 1. Abstraction Layer vs Converter
**Decision**: Used abstraction layer (dual native support)
**Rationale**: Maintains full fidelity of both frameworks, allows framework-specific optimizations

### 2. Metadata Approach
**Decision**: Required metadata dictionary in model file
**Rationale**: 
- Gurobipy models lack introspection capabilities of Pyomo
- Metadata provides necessary structure information
- Avoids complex naming convention parsing
- Allows users to provide domain-specific descriptions

### 3. Naming Conventions
**Decision**: Recommend `component[index]` format
**Rationale**:
- Enables parsing of indexed components
- Consistent with mathematical notation
- Easier to extract base names and indices

## Metadata Structure

Required fields in `model._optichat_metadata`:

```python
{
    'sets': {
        'set_name': {
            'description': str,
            'elements': list
        }
    },
    'parameters': {
        'param_name': {
            'description': str,
            'is_indexed': bool,
            'index_set': list or None,
            'is_RHS': bool,  # True if RHS, False if LHS coefficient
            'is_mutable': bool,
            'cons_in': list  # Constraint names using this param
        }
    },
    'variables': {
        'var_name': {
            'description': str
        }
    },
    'constraints': {
        'constr_name': {
            'description': str,
            'params_in': set  # Parameter names in this constraint
        }
    },
    'objective': {
        'name': str,
        'description': str
    }
}
```

## Testing Strategy

Created `examples/simple_gurobi_model.py` as a test case:
- Production planning problem
- Indexed variables and constraints
- Multiple parameters with different characteristics
- Complete metadata example
- Can be uploaded directly to OptiChat

## Known Limitations

1. **Metadata Required**: Users must manually create metadata dictionary
2. **LP Only for Sensitivity**: Gurobi sensitivity analysis only works for LP
3. **Index Parsing**: Complex index structures may need careful naming
4. **IIS Simplification**: Gurobi feasibility restoration is simplified compared to Pyomo version

## Future Enhancements

Potential improvements for future versions:

1. **Metadata Generator**: Tool to help users generate metadata from existing models
2. **Index Convention Parser**: Better handling of various naming conventions
3. **Enhanced IIS Analysis**: More sophisticated feasibility restoration for Gurobi
4. **Dual Value Access**: Better sensitivity analysis for Gurobi models
5. **Constraint Modification**: More robust parameter modification in Gurobi constraints

## Files Changed/Created

### Created:
- `model_adapter.py` - Abstraction layer (195 lines)
- `GUROBI_SUPPORT.md` - Documentation (270 lines)
- `examples/simple_gurobi_model.py` - Example model (110 lines)
- `IMPLEMENTATION_SUMMARY.md` - This file

### Modified:
- `extractor.py` - Added gurobi2json, detect_model_framework, updated initial_loading
- `internal_tools.py` - Added 4 Gurobi tool functions + dispatch function (~400 lines added)
- `prompts.py` - Updated prompts with Gurobi examples
- `app.py` - Updated UI to display framework type
- `README.md` - Added Gurobi support section

## Testing Checklist

To verify the implementation:

- [ ] Upload Pyomo model - should work as before
- [ ] Upload Gurobi model with metadata - should detect as Gurobi
- [ ] Model interpretation works for both frameworks
- [ ] Feasibility restoration works for infeasible Gurobi models
- [ ] Sensitivity analysis works for Gurobi LP models
- [ ] Component retrieval works for Gurobi models
- [ ] Modification evaluation works for Gurobi models
- [ ] Code generation provides correct syntax for detected framework
- [ ] UI displays correct framework type

## Backward Compatibility

All existing Pyomo functionality remains unchanged:
- Existing Pyomo models work identically
- No changes to Pyomo-specific logic
- PyomoAdapter wraps existing functions without modification
- Default framework is 'pyomo' for backward compatibility

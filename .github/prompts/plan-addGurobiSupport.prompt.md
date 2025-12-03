## Plan: Add Gurobipy Support to OptiChat

OptiChat currently only supports Pyomo models. This plan adds native Gurobipy support through an abstraction layer architecture, allowing users to upload and interact with optimization models written in either framework while maintaining all existing functionality.

### Steps

1. **Create abstraction layer** with base class `AbstractOptimizationModel` defining unified interface (`get_variables()`, `get_constraints()`, `solve()`, `extract_iis()`, `to_json()`, etc.) and implement `PyomoAdapter` wrapping existing logic and `GurobiAdapter` with Gurobi-specific implementations.

2. **Implement model type detection** in `initial_loading` to analyze uploaded code for `import pyomo` vs `import gurobipy`, instantiate appropriate adapter, and store `model_type` in `models_dict`.

3. **Create `gurobi2json` converter** to extract variables via `model.getVars()`, constraints via `model.getConstrs()`, objective via `model.getObjective()`, parse variable/constraint names to infer index structure, and handle IIS extraction using `model.computeIIS()` and `.IISConstr` attributes.

4. **Implement Gurobi internal tools** in `internal_tools.py` with dual code paths: `feasibility_restoration_gurobi` using `model.copy()` and constraint reconstruction, `sensitivity_analysis_gurobi` accessing `constr.Pi` for duals, `components_retrival_gurobi` using name-based getters, and `evaluate_modification_gurobi` modifying constraints via `model.remove()` and `model.addConstr()`.

5. **Add metadata support** requiring users to include metadata dict in Gurobi model files documenting parameters, their descriptions, RHS vs LHS location, and associated constraints, then parse this during `gurobi2json` to populate JSON representation.

6. **Update prompts and UI** in `prompts.py` to include Gurobi syntax examples alongside Pyomo, modify code generation templates (lines 311-366), add Gurobi API references, and update `app.py` to display detected model type and handle framework-specific error messages.

### Further Considerations

1. **Should we use abstraction layer (dual native support) or converter approach (Gurobi-to-Pyomo on upload)?** Converter is simpler (1-2 weeks vs 4-6 weeks) but loses some Gurobi-native capabilities. Abstraction maintains full fidelity but requires extensive refactoring.

2. **How should users provide metadata for Gurobi models?** Options: A) Require standardized naming conventions (`param_demand`, `var_production_1_2`), B) Include metadata dict in model file, C) Upload separate JSON metadata file alongside .py file.

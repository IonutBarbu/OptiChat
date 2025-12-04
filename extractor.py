import pyomo.environ as pe
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
from pyomo.contrib.iis import *
from pyomo.core.expr.visitor import identify_mutable_parameters, identify_variables
from pyomo.core.expr.calculus.derivatives import differentiate
import re
import os
import io
import sys
import importlib
from contextlib import redirect_stdout
import signal
import copy
from typing import Union
from io import StringIO


def find_lhs_params(constraint_expr, param_names, var_names):
    lhs_params = set()
    lhs_params_coefs = {}

    # Handle bracketed terms (indexes)
    # Step 1: Extract bracketed terms from the constraint expression
    bracketed_terms = re.findall(r'\[.*?\]', constraint_expr)
    # Step 2: Replace bracketed terms with placeholders
    placeholders = {}
    modified_expr = constraint_expr
    for i, term in enumerate(bracketed_terms):
        placeholder = f" __PLACEHOLDER_{i}__ "
        placeholders.update({placeholder: term})
        modified_expr = modified_expr.replace(term, placeholder, 1)
    # Step 3: Split the modified expression around non-word characters, preserving placeholders
    parts = re.split('(\W)', modified_expr)
    parts = [part for part in parts if part.strip() != '']
    # Step 4: Re-insert bracketed terms in place of placeholders
    final_parts = []
    for part in parts:
        if part.startswith("__PLACEHOLDER"):
            original_term = placeholders[" " + part + " "]
            final_parts.append(original_term)
        else:
            final_parts.append(part)
    parts = final_parts

    def locate_name(names, parts):
        dict = {}
        for name in names:
            if name in parts:
                # find the idx of param_name/var_name in parts
                name_idx = [i for i, x in enumerate(parts) if x == name]
                dict[name] = {'indexes': name_idx}
        return dict

    def in_parentheses(index):
        lbrace = 0
        rbrace = 0
        for i in range(index):
            if parts[i] == '(':
                lbrace += 1
            elif parts[i] == ')':
                rbrace += 1
        return lbrace, rbrace

    param_dict = locate_name(param_names, parts)
    var_dict = locate_name(var_names, parts)

    for param_name, param_indexes in param_dict.items():
        for param_idx in param_indexes['indexes']:
            param_lbrace, param_rbrace = in_parentheses(param_idx)
            for var_name, var_indexes in var_dict.items():
                for var_idx in var_indexes['indexes']:
                    var_lbrace, var_rbrace = in_parentheses(var_idx)
                    if (param_lbrace, param_rbrace) == (var_lbrace, var_rbrace):
                        # in the same parentheses
                        for i in range(min(param_idx, var_idx), max(param_idx, var_idx)):
                            if parts[i] in ['+', '-', '=', '<', '>']:
                                break
                            elif parts[i] in ['*', '/']:
                                lhs_params.add(param_name)
                                break
                    elif abs(param_lbrace - var_lbrace) == 1 and param_rbrace - var_rbrace == 0:
                        # one parenthesis in between
                        for i in range(min(param_idx, var_idx), max(param_idx, var_idx)):
                            if parts[i] in ['+', '-',  '=', '<', '>', '(']:
                                break
                            elif parts[i] in ['*', '/']:
                                lhs_params.add(param_name)
                                break
                    elif param_lbrace - var_lbrace == 0 and abs(param_rbrace - var_rbrace) == 1:
                        # one parenthesis in between
                        for i in range(max(param_idx, var_idx), min(param_idx, var_idx), -1):
                            if parts[i] in ['+', '-',  '=', '<', '>', ')']:
                                break
                            elif parts[i] in ['*', '/']:
                                lhs_params.add(param_name)
                                break
    return lhs_params


def pyomo2json(model, termination_condition='Unknown'):
    """
    Convert a Pyomo model to a JSON string.
    """
    model_dict = {}
    # model_dict["model name"] = model.name
    model_dict["model class"] = model
    model_dict["model status"] = termination_condition
    model_dict["model type"] = "LP"
    model_dict["model description"] = None

    model_dict["components"] = {}

    model_dict["components"]["sets"] = {}
    for set_name, _set in model.component_map(pe.Set).items():
        set_dict = {}
        set_dict['name'] = set_name
        set_dict['is_indexed'] = False
        set_dict["description"] = _set.doc
        model_dict["components"]["sets"][set_name] = set_dict

    model_dict["components"]["parameters"] = {}
    for param_name, param in model.component_map(pe.Param).items():
        param_dict = {}
        param_dict['name'] = param_name
        if param.is_indexed():
            param_dict['is_indexed'] = param.is_indexed()
            param_dict["index_set"] = param.index_set()  # store the index set object
        else:
            param_dict['is_indexed'] = param.is_indexed()
            param_dict["index_set"] = None  # non_indexed_param[None] is accessible
        if param.mutable:
            param_dict["is_RHS"] = True  # revisit later
            param_dict["is_mutable"] = True
        else:
            param_dict["is_RHS"] = False   # revisit later
            param_dict["is_mutable"] = False
        param_dict["cons_in"] = set()

        param_dict["description"] = param.doc
        model_dict["components"]["parameters"][param_name] = param_dict

        # add description to default sets
        set_name = param_name + '_index'
        if set_name in model_dict["components"]["sets"]:
            model_dict["components"]["sets"][set_name]["description"] = f"index set for {param_name} parameter"

    model_dict["components"]["variables"] = {}
    for var_name, var in model.component_map(pe.Var).items():
        var_dict = {}
        var_dict['name'] = var_name
        if var.is_indexed():
            var_dict['is_indexed'] = var.is_indexed()
            var_dict["index_set"] = var.index_set()  # store the index set object
        else:
            var_dict['is_indexed'] = var.is_indexed()
            var_dict["index_set"] = None  # non_indexed_var[None] is accessible
        var_dict["cons_in"] = set()
        var_dict["description"] = var.doc
        model_dict["components"]["variables"][var_name] = var_dict

        # check if the model is an IP
        if model_dict["model type"] != "IP":
            for var_idx in var:
                var_i = var[var_idx]
                if var_i.is_binary():
                    model_dict["model type"] = "IP"

        # add description to default sets
        set_name = var_name + '_index'
        if set_name in model_dict["components"]["sets"]:
            model_dict["components"]["sets"][set_name]["description"] = f"index set for {var_name} variable"

    model_dict["components"]["constraints"] = {}
    for con_name, con in model.component_map(pe.Constraint).items():
        con_dict = {}
        con_dict['name'] = con_name
        if con.is_indexed():
            con_dict['is_indexed'] = con.is_indexed()
            con_dict["index_set"] = con.index_set()  # store the index set object
        else:
            con_dict['is_indexed'] = con.is_indexed()
            con_dict["index_set"] = None  # non_indexed_con[None] is accessible
        # for each type of constraint, identify the mutable parameter names AND identify the RHS parameters
        con_dict['params_in'] = set()
        con_dict['vars_in'] = set()
        for con_idx in con:
            con_i = con[con_idx]
            expr_params = identify_mutable_parameters(con_i.expr)
            expr_vars = identify_variables(con_i.expr)
            for p in expr_params:
                p_name = p.name.split("[")[0]
                con_dict['params_in'].add(p_name)
                model_dict["components"]["parameters"][p_name]["cons_in"].add(con_name)
            for v in expr_vars:
                v_name = v.name.split("[")[0]
                con_dict['vars_in'].add(v_name)
                model_dict["components"]["variables"][v_name]["cons_in"].add(con_name)

            con_i_expr = con_i.expr.to_string()
            lhs_params = find_lhs_params(con_i_expr,
                                         model_dict["components"]["parameters"].keys(),
                                         model_dict["components"]["variables"].keys())
            for lhs_param in lhs_params:
                model_dict["components"]["parameters"][lhs_param]["is_RHS"] = False

        con_dict["description"] = con.doc
        model_dict["components"]["constraints"][con_name] = con_dict

        # add description to default sets
        set_name = con_name + '_index'
        if set_name in model_dict["components"]["sets"]:
            model_dict["components"]["sets"][set_name]["description"] = f"index set for {con_name} constraint"

    model_dict["components"]["objective"] = {}
    for obj_name, obj in model.component_map(pe.Objective).items():
        obj_dict = {}
        obj_dict['name'] = obj_name
        if obj.sense == 1:
            obj_dict["sense"] = 'minimize'
        elif obj.sense == -1:
            obj_dict["sense"] = 'maximize'

        if termination_condition in [TerminationCondition.infeasible, TerminationCondition.infeasibleOrUnbounded]:
            obj_dict["optimal_value"] = "N/A due to infeasibility"
        else:
            obj_dict["optimal_value"] = obj()
        # if termination_condition == "optimal":
        #     obj_dict["optimal_value"] = obj()
        # elif termination_condition == "maxTimeLimit":
        #     obj_dict["optimal_value"] = obj()
        # elif termination_condition == "infeasible":
        #     obj_dict["optimal_value"] = "N/A due to infeasibility"

        obj_dict['is_indexed'] = False
        obj_dict["description"] = obj.doc
        model_dict["components"]["objective"][obj_name] = obj_dict

    return model_dict


def gurobi2json(model, termination_condition='Unknown'):
    """
    Convert a Gurobipy model to a JSON string compatible with OptiChat.
    """
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError:
        raise ImportError("gurobipy is required for Gurobi model support")
    
    model_dict = {}
    model_dict["model class"] = model
    model_dict["model status"] = termination_condition
    model_dict["model type"] = "LP"
    model_dict["model description"] = None
    model_dict["components"] = {}
    
    # Extract metadata if available (user should provide this in model file)
    metadata = getattr(model, '_optichat_metadata', {})
    
    # Sets extraction
    model_dict["components"]["sets"] = {}
    sets_info = metadata.get('sets', {})
    for set_name, set_data in sets_info.items():
        set_dict = {
            'name': set_name,
            'is_indexed': False,
            'description': set_data.get('description', f'Set {set_name}')
        }
        model_dict["components"]["sets"][set_name] = set_dict
    
    # Parameters extraction
    model_dict["components"]["parameters"] = {}
    params_info = metadata.get('parameters', {})
    for param_name, param_data in params_info.items():
        param_dict = {
            'name': param_name,
            'is_indexed': param_data.get('is_indexed', False),
            'index_set': param_data.get('index_set', None),
            'is_RHS': param_data.get('is_RHS', True),
            'is_mutable': param_data.get('is_mutable', True),
            'cons_in': set(param_data.get('cons_in', [])),
            'description': param_data.get('description', f'Parameter {param_name}')
        }
        model_dict["components"]["parameters"][param_name] = param_dict
    
    # Variables extraction
    model_dict["components"]["variables"] = {}
    variables = model.getVars()
    
    # Group variables by base name (before index)
    var_groups = {}
    for var in variables:
        var_name = var.VarName
        # Parse variable name to extract base name and indices
        if '[' in var_name:
            base_name = var_name.split('[')[0]
            index_str = var_name.split('[')[1].split(']')[0]
            indices = tuple(index_str.split(',')) if ',' in index_str else (index_str,)
        else:
            base_name = var_name
            indices = None
        
        if base_name not in var_groups:
            var_groups[base_name] = {
                'indices': [],
                'is_binary': var.VType == GRB.BINARY,
                'is_integer': var.VType in [GRB.INTEGER, GRB.BINARY]
            }
        if indices:
            var_groups[base_name]['indices'].append(indices)
    
    for var_name, var_info in var_groups.items():
        var_dict = {
            'name': var_name,
            'is_indexed': len(var_info['indices']) > 0,
            'index_set': var_info['indices'] if var_info['indices'] else None,
            'cons_in': set(),
            'description': metadata.get('variables', {}).get(var_name, {}).get('description', f'Variable {var_name}')
        }
        model_dict["components"]["variables"][var_name] = var_dict
        
        # Check if model is IP
        if model_dict["model type"] != "IP" and var_info['is_binary']:
            model_dict["model type"] = "IP"
    
    # Constraints extraction
    model_dict["components"]["constraints"] = {}
    constraints = model.getConstrs()
    
    # Group constraints by base name
    con_groups = {}
    for con in constraints:
        con_name = con.ConstrName
        # Parse constraint name to extract base name and indices
        if '[' in con_name:
            base_name = con_name.split('[')[0]
            index_str = con_name.split('[')[1].split(']')[0]
            indices = tuple(index_str.split(',')) if ',' in index_str else (index_str,)
        else:
            base_name = con_name
            indices = None
        
        if base_name not in con_groups:
            con_groups[base_name] = {
                'indices': [],
                'vars_in': set(),
                'params_in': set()
            }
        if indices:
            con_groups[base_name]['indices'].append(indices)
        
        # Extract variables from constraint
        row = model.getRow(con)
        for i in range(row.size()):
            var = row.getVar(i)
            var_base_name = var.VarName.split('[')[0] if '[' in var.VarName else var.VarName
            con_groups[base_name]['vars_in'].add(var_base_name)
    
    for con_name, con_info in con_groups.items():
        con_dict = {
            'name': con_name,
            'is_indexed': len(con_info['indices']) > 0,
            'index_set': con_info['indices'] if con_info['indices'] else None,
            'params_in': metadata.get('constraints', {}).get(con_name, {}).get('params_in', set()),
            'vars_in': con_info['vars_in'],
            'description': metadata.get('constraints', {}).get(con_name, {}).get('description', f'Constraint {con_name}')
        }
        model_dict["components"]["constraints"][con_name] = con_dict
        
        # Update which constraints each variable appears in
        for var_name in con_info['vars_in']:
            if var_name in model_dict["components"]["variables"]:
                model_dict["components"]["variables"][var_name]["cons_in"].add(con_name)
    
    # Objective extraction
    model_dict["components"]["objective"] = {}
    obj = model.getObjective()
    obj_name = metadata.get('objective', {}).get('name', 'obj')
    
    obj_dict = {
        'name': obj_name,
        'sense': 'minimize' if model.ModelSense == GRB.MINIMIZE else 'maximize',
        'is_indexed': False,
        'description': metadata.get('objective', {}).get('description', 'Objective function')
    }
    
    if termination_condition in [TerminationCondition.infeasible, TerminationCondition.infeasibleOrUnbounded]:
        obj_dict["optimal_value"] = "N/A due to infeasibility"
    else:
        try:
            obj_dict["optimal_value"] = model.ObjVal
        except:
            obj_dict["optimal_value"] = "N/A"
    
    model_dict["components"]["objective"][obj_name] = obj_dict
    
    return model_dict


def iis2json(ilp_path, model_dict):
    constr_names = set()
    iis_dict = {}
    if model_dict["model status"] in [TerminationCondition.infeasible, TerminationCondition.infeasibleOrUnbounded]:
        with open(ilp_path, 'r') as file:
            ilp_string = file.read()
        file.close()
        ilp_lines = ilp_string.split("\n")
        for iis_line in ilp_lines:
            if ":" in iis_line:
                constr_name = iis_line.split(":")[0].split("(")[0].replace(" ", "")
                constr_names.add(constr_name)

        for const_name in constr_names:
            iis_dict[const_name] = {"params_in": model_dict["components"]["constraints"][const_name]['params_in'],
                                    "vars_in": model_dict["components"]["constraints"][const_name]['vars_in']}
    model_dict['iis'] = iis_dict

    iis_description = iis_translation(model_dict)
    model_dict["iis_description"] = iis_description

    return model_dict


def initial_loading(file, is_uploaded=True):
    if is_uploaded:
        code = file.getvalue().decode("utf-8")
        spec = importlib.util.spec_from_loader("uploaded_model", loader=None)
        uploaded_model = importlib.util.module_from_spec(spec)
        sys.modules["uploaded_model"] = uploaded_model

        # Execute the code in the context of the new module
        exec(code, uploaded_model.__dict__)

        model = uploaded_model.model
        model_name = os.path.splitext(file.name)[0]

    else:
        with open(file, 'r') as f:
            code = f.read()
        f.close()
        directory_path = os.path.dirname(file)
        model_name = os.path.splitext(os.path.basename(file))[0]
        module = importlib.import_module(directory_path + '.' + model_name)
        model = module.model

    # Detect model framework type by analyzing imports in the code
    model_framework = detect_model_framework(code)
    print(f"Detected model framework: {model_framework}")
    
    # Create appropriate adapter
    from model_adapter import create_adapter
    adapter = create_adapter(model, code, model_framework)
    
    # Solve the model using the adapter
    status, termination_condition = adapter.solve()
    print(f"Model {model_name} loaded, "
          f"Solver Status: {status}, Termination Condition: {termination_condition}")

    # Handle IIS extraction for infeasible models
    ilp_path = ""
    if termination_condition in [TerminationCondition.infeasible, TerminationCondition.infeasibleOrUnbounded]:
        if not os.path.exists(f'logs/ilps'):
            os.makedirs(f'logs/ilps')
        ilp_path = os.path.abspath('logs/ilps/' + model_name + ".ilp")
        adapter.extract_iis(ilp_path)
        print('model name:', model_name)
        print(f'ilp path: {ilp_path}')

    # Convert model to JSON representation
    model_dict = adapter.to_json()
    model_dict = iis2json(ilp_path, model_dict)
    model_dict.update({'code': code, 'model_framework': model_framework})
    models_dict = {'model_representation': {}, 'model_1': model_dict, }
    return models_dict, code


def detect_model_framework(code: str) -> str:
    """
    Detect whether the model is Pyomo or Gurobipy based on import statements.
    
    Args:
        code: Source code as string
        
    Returns:
        'pyomo' or 'gurobi'
    """
    code_lower = code.lower()
    
    # Check for Gurobi imports
    gurobi_patterns = [
        'import gurobipy',
        'from gurobipy',
        'import gurobi',
        'from gurobi'
    ]
    
    # Check for Pyomo imports
    pyomo_patterns = [
        'import pyomo',
        'from pyomo'
    ]
    
    has_gurobi = any(pattern in code_lower for pattern in gurobi_patterns)
    has_pyomo = any(pattern in code_lower for pattern in pyomo_patterns)
    
    if has_gurobi and not has_pyomo:
        return 'gurobi'
    elif has_pyomo and not has_gurobi:
        return 'pyomo'
    elif has_gurobi and has_pyomo:
        # If both are present, prioritize based on which appears first
        gurobi_pos = min([code_lower.find(p) for p in gurobi_patterns if p in code_lower])
        pyomo_pos = min([code_lower.find(p) for p in pyomo_patterns if p in code_lower])
        return 'gurobi' if gurobi_pos < pyomo_pos else 'pyomo'
    else:
        # Default to Pyomo for backward compatibility
        return 'pyomo'


def iis_translation(model_dict):
    iis_dict = model_dict['iis']
    translation = ""
    for con_name in iis_dict:
        param_names = iis_dict[con_name]['params_in']
        var_names = iis_dict[con_name]['vars_in']
        translation_per_con = f'Constraints {con_name} are in the IIS, with the following parameters: '
        for i, param_name in enumerate(param_names):
            if i == len(param_names) - 1:
                translation_per_con += f'{param_name}; and with the following variables: '
            else:
                translation_per_con += f'{param_name}, '
        for i, var_name in enumerate(var_names):
            if i == len(var_names) - 1:
                translation_per_con += f'{var_name}. \n'
            else:
                translation_per_con += f'{var_name}, '
        translation += translation_per_con
    return translation


def update_model_representation(models_dict, model_name='model_1'):
    models_dict['model_representation'] = {}
    model_representation = models_dict['model_representation']
    ref_model_dict = models_dict[model_name]
    # exclude model class
    model_representation['code'] = ref_model_dict['code']
    model_representation["model status"] = ref_model_dict["model status"]
    model_representation["model type"] = ref_model_dict["model type"]
    model_representation["model description"] = ref_model_dict["model description"]
    model_representation["components"] = {}
    component_types = ["sets", "parameters", "variables", "constraints", "objective"]
    # copy everything except index_set
    for component_type in component_types:
        model_representation["components"][component_type] = {}
        for component_name, component_info in ref_model_dict["components"][component_type].items():
            model_representation["components"][component_type][component_name] = {}
            for key, value in component_info.items():
                if key != "index_set":
                    model_representation["components"][component_type][component_name][key] = value
    if 'iis' in ref_model_dict:
        model_representation["iis"] = ref_model_dict["iis"]
    if 'iis_description' in ref_model_dict:
        model_representation["iis_description"] = ref_model_dict["iis_description"]


# def old_update_model_representation(models_dict, model_name='model_1'):
#     ref_model_dict = models_dict[model_name]
#     models_dict['model_representation'] = copy.deepcopy(ref_model_dict)
#     for component_type, components in ref_model_dict["components"].items():
#         for component_name, component_info in components.items():
#             if "index_set" in component_info:
#                 del models_dict['model_representation']["components"][component_type][component_name]["index_set"]


def extract_component_descriptions(models_dict):
    ref_model_dict = models_dict['model_representation']["components"]
    component_descriptions = copy.deepcopy(ref_model_dict)
    return component_descriptions


def replace(src_code: str, old_code: str, new_code: str) -> str:
    """
    TAKEN FROM AUTOGEN: https://microsoft.github.io/autogen/docs/notebooks/agentchat_nestedchat_optiguide/
    Inserts new code into the source code by replacing a specified old
    code block.

    Args:
        src_code (str): The source code to modify.
        old_code (str): The code block to be replaced.
        new_code (str): The new code block to insert.

    Returns:
        str: The modified source code with the new code inserted.

    Raises:
        None

    Example:
        src_code = 'def hello_world():\n    # CODE GOES HERE'
        old_code = '# CODE GOES HERE'
        new_code = 'print("Bonjour, monde!")\nprint("Hola, mundo!")'
        modified_code = _replace(src_code, old_code, new_code)
        print(modified_code)
        # Output:
        # def hello_world():
        #     print("Bonjour, monde!")
        #     print("Hola, mundo!")
    """
    pattern = r"( *){old_code}".format(old_code=old_code)
    head_spaces = re.search(pattern, src_code, flags=re.DOTALL).group(1)
    new_code = "\n".join([head_spaces + line for line in new_code.split("\n")])
    rst = re.sub(pattern, new_code, src_code)
    return rst


def insert_code(src_code: str, new_lines: str, code_type: str) -> str:
    """
    ADAPTED FROM AUTOGEN: https://microsoft.github.io/autogen/docs/notebooks/agentchat_nestedchat_optiguide/

    insert a code patch into the source code.
    """
    # # # for now, we have # OPTICHAT REVISION CODE GOES HERE and # OPTICHAT PRINT CODE GOES HERE
    # # return replace(src_code, '# CODE GOES HERE', new_lines)
    # if code_type == 'REVISION':
    #     return replace(src_code, f"# OPTICHAT {code_type} CODE GOES HERE", new_lines)
    # elif code_type == 'PRINT':
    #     return replace(src_code, f"# OPTICHAT {code_type} CODE GOES HERE", new_lines)
    # else:
    #     raise ValueError(f"Invalid code type: {code_type}")
    return replace(src_code, f"# YOUR CODE GOES HERE", new_lines)


def run_with_exec(src_code: str):
    locals_dict = {}
    output = io.StringIO()

    try:
        with redirect_stdout(output):
            exec(src_code, locals_dict, locals_dict)
        return output.getvalue()
    except Exception as e:
        import traceback
        return output.getvalue() + "\n" + traceback.format_exc()


def var_in_con(constraint_expr):
    vars_list = list(identify_variables(constraint_expr))
    return vars_list


def param_in_con(constraint_expr):
    params_list = list(identify_mutable_parameters(constraint_expr))
    return params_list


def get_files_generator(folder_name):
    """
    Get all the .py files in the folder
    folder_name = "video_showcase"
    py_file_names = get_files_generator(folder_name)
    a generator of ['video_showcase/pdi_inf_1.py', 'video_showcase/pdi_inf_2.py']
    """
    files_and_dirs = os.listdir(folder_name)
    for f in files_and_dirs:
        if os.path.isfile(os.path.join(folder_name, f)) and f.endswith('.py'):
            yield os.path.join(folder_name, f)


def get_files(folder_name):
    """
    Get all the .py files in the folder
    folder_name = "video_showcase"
    py_file_names = get_files_generator(folder_name)
    ['video_showcase/pdi_inf_1.py', 'video_showcase/pdi_inf_2.py']
    then split it into two lists, one is for feasible models, the other is for infeasible models
    """
    files_and_dirs = os.listdir(folder_name)
    infeasible_files = []
    feasible_files = []
    for f in files_and_dirs:
        if os.path.isfile(os.path.join(folder_name, f)) and f.endswith('.py'):
            if '_inf_' in f:
                infeasible_files.append(os.path.join(folder_name, f))
            else:
                feasible_files.append(os.path.join(folder_name, f))
    return infeasible_files, feasible_files


# def get_skipJSON_old(model_representation):
#     """
#     get the model description and description of every component
#     skipJSON is the json that help skip the process of calling interpreter (interpret, illustrate, infer)
#     """
#     skipJSON = {"model description": model_representation["model description"],
#                  "components": {"sets": {},
#                                 "parameters": {},
#                                 "variables": {},
#                                 "constraints": {},
#                                 "objective": {}}
#                  }
#     for component_type in ["sets", "parameters", "variables", "constraints", "objective"]:
#         for component_name, component_dict in model_representation["components"][component_type].items():
#             skipJSON["components"][component_type][component_name] = component_dict["description"]
#
#     return skipJSON


def get_skipJSON(model_representation):
    """
    get the model description and description of every component
    skipJSON is the json that help skip the process of calling interpreter (interpret, illustrate, infer)
    """
    COMPONENT_TYPES = ["sets", "parameters", "variables", "constraints", "objective"]
    skipJSON = {
        "model description": model_representation["model description"],
        "components": {
            component_type: {
                component_name: component_dict["description"]
                for component_name, component_dict in model_representation["components"][component_type].items()
            }
            for component_type in COMPONENT_TYPES
        }
    }
    return skipJSON


def feed_skipJSON(skipJSON, models_dict, queried_model='model_1'):
    """
    feed the skipJSON to the models_dict['queried_model']
    """
    COMPONENT_TYPES = ["sets", "parameters", "variables", "constraints", "objective"]
    model_dict = models_dict[queried_model]
    model_dict['model description'] = skipJSON['model description']
    for component_type in COMPONENT_TYPES:
        for component_name, component_dict in model_dict["components"][component_type].items():
            component_dict['description'] = skipJSON['components'][component_type][component_name]
    return models_dict
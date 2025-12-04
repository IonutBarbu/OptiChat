"""
Abstraction layer for optimization model frameworks.
Provides a unified interface for Pyomo and Gurobipy models.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import pyomo.environ as pe
from pyomo.opt import SolverFactory, TerminationCondition
from pyomo.contrib.iis import write_iis


class AbstractOptimizationModel(ABC):
    """Base class defining unified interface for optimization models."""
    
    def __init__(self, model, code: str):
        self.model = model
        self.code = code
        self.termination_condition = None
        self.solver_status = None
        
    @abstractmethod
    def solve(self, solver_name: str = 'gurobi', **kwargs) -> Tuple[Any, Any]:
        """
        Solve the optimization model.
        
        Returns:
            Tuple of (solver_status, termination_condition)
        """
        pass
    
    @abstractmethod
    def to_json(self) -> Dict[str, Any]:
        """
        Convert model to JSON representation.
        
        Returns:
            Dictionary representation of the model
        """
        pass
    
    @abstractmethod
    def extract_iis(self, output_path: str) -> str:
        """
        Extract Irreducible Inconsistent Subsystem for infeasible models.
        
        Args:
            output_path: Path to save IIS file
            
        Returns:
            Path to the IIS file
        """
        pass
    
    @abstractmethod
    def clone(self):
        """Create a deep copy of the model."""
        pass
    
    @abstractmethod
    def get_model_type(self) -> str:
        """Return the framework type ('pyomo' or 'gurobi')."""
        pass


class PyomoAdapter(AbstractOptimizationModel):
    """Adapter for Pyomo models."""
    
    def __init__(self, model, code: str):
        super().__init__(model, code)
        
    def solve(self, solver_name: str = 'gurobi', **kwargs) -> Tuple[Any, Any]:
        """Solve the Pyomo model."""
        solver = SolverFactory(solver_name)
        results = solver.solve(self.model, tee=kwargs.get('tee', True))
        self.solver_status = results.solver.status
        self.termination_condition = results.solver.termination_condition
        return self.solver_status, self.termination_condition
    
    def to_json(self) -> Dict[str, Any]:
        """Convert Pyomo model to JSON representation."""
        from extractor import pyomo2json
        return pyomo2json(self.model, termination_condition=self.termination_condition)
    
    def extract_iis(self, output_path: str) -> str:
        """Extract IIS for infeasible Pyomo model."""
        if self.termination_condition not in [TerminationCondition.infeasible, 
                                               TerminationCondition.infeasibleOrUnbounded]:
            return ""
        
        ilp_name = write_iis(self.model, output_path, solver="gurobi")
        return output_path
    
    def clone(self):
        """Create a deep copy of the Pyomo model."""
        return self.model.clone()
    
    def get_model_type(self) -> str:
        """Return 'pyomo'."""
        return "pyomo"


class GurobiAdapter(AbstractOptimizationModel):
    """Adapter for Gurobipy models."""
    
    def __init__(self, model, code: str):
        super().__init__(model, code)
        
    def solve(self, solver_name: str = 'gurobi', **kwargs) -> Tuple[str, str]:
        """Solve the Gurobipy model."""
        try:
            self.model.optimize()
            
            # Map Gurobi status to Pyomo-like status
            from gurobipy import GRB
            
            if self.model.status == GRB.OPTIMAL:
                self.solver_status = "ok"
                self.termination_condition = "optimal"
            elif self.model.status == GRB.INFEASIBLE:
                self.solver_status = "warning"
                self.termination_condition = TerminationCondition.infeasible
            elif self.model.status == GRB.INF_OR_UNBD:
                self.solver_status = "warning"
                self.termination_condition = TerminationCondition.infeasibleOrUnbounded
            elif self.model.status == GRB.UNBOUNDED:
                self.solver_status = "warning"
                self.termination_condition = TerminationCondition.unbounded
            elif self.model.status == GRB.TIME_LIMIT:
                self.solver_status = "aborted"
                self.termination_condition = "maxTimeLimit"
            else:
                self.solver_status = "unknown"
                self.termination_condition = "unknown"
                
            return self.solver_status, self.termination_condition
            
        except Exception as e:
            self.solver_status = "error"
            self.termination_condition = "error"
            print(f"Error solving Gurobi model: {e}")
            return self.solver_status, self.termination_condition
    
    def to_json(self) -> Dict[str, Any]:
        """Convert Gurobipy model to JSON representation."""
        from extractor import gurobi2json
        return gurobi2json(self.model, termination_condition=self.termination_condition)
    
    def extract_iis(self, output_path: str) -> str:
        """Extract IIS for infeasible Gurobipy model."""
        if self.termination_condition not in [TerminationCondition.infeasible, 
                                               TerminationCondition.infeasibleOrUnbounded]:
            return ""
        
        try:
            self.model.computeIIS()
            self.model.write(output_path)
            return output_path
        except Exception as e:
            print(f"Error computing IIS: {e}")
            return ""
    
    def clone(self):
        """Create a deep copy of the Gurobipy model."""
        return self.model.copy()
    
    def get_model_type(self) -> str:
        """Return 'gurobi'."""
        return "gurobi"


def create_adapter(model, code: str, model_framework: str) -> AbstractOptimizationModel:
    """
    Factory function to create appropriate adapter based on framework.
    
    Args:
        model: The optimization model object
        code: Source code as string
        model_framework: Either 'pyomo' or 'gurobi'
        
    Returns:
        Appropriate adapter instance
    """
    if model_framework == 'pyomo':
        return PyomoAdapter(model, code)
    elif model_framework == 'gurobi':
        return GurobiAdapter(model, code)
    else:
        raise ValueError(f"Unsupported framework: {model_framework}. Use 'pyomo' or 'gurobi'.")

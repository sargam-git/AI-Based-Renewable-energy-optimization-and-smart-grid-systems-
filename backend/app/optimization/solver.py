"""Direct HiGHS binding avoids a degenerate presolve issue seen in older SciPy wrappers."""
from types import SimpleNamespace
import numpy as np
import highspy

def solve_milp(*,c,integrality,bounds,constraints,options):
    h=highspy.Highs(); h.setOptionValue('output_flag',False); h.setOptionValue('threads',1); h.setOptionValue('random_seed',42)
    h.setOptionValue('time_limit',float(options.get('time_limit',25)))
    h.setOptionValue('mip_rel_gap',float(options.get('mip_rel_gap',1e-7)))
    h.setOptionValue('mip_abs_gap',1e-6)
    n=len(c); matrix=constraints.A.tocsr()
    costs=np.asarray(c,dtype=float); lower=np.asarray(bounds.lb,dtype=float); upper=np.asarray(bounds.ub,dtype=float)
    h.addCols(n,costs,lower,upper,0,np.array([],dtype=np.int32),np.array([],dtype=np.int32),np.array([],dtype=float))
    h.addRows(matrix.shape[0],np.asarray(constraints.lb,dtype=float),np.asarray(constraints.ub,dtype=float),matrix.nnz,matrix.indptr.astype(np.int32),matrix.indices.astype(np.int32),matrix.data.astype(float))
    indices=np.flatnonzero(integrality)
    if len(indices): h.changeColsIntegrality(len(indices),indices.astype(np.int32),np.full(len(indices),highspy.HighsVarType.kInteger))
    h.run(); status=h.getModelStatus(); sol=h.getSolution(); info=h.getInfo()
    success=status==highspy.HighsModelStatus.kOptimal and sol.value_valid
    return SimpleNamespace(success=success,x=np.asarray(sol.col_value,dtype=float) if success else None,fun=float(info.objective_function_value),mip_gap=float(info.mip_gap),message=str(h.modelStatusToString(status)))

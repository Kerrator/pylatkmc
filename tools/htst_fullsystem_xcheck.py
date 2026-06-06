"""Lean full-system IRA cross-check: fast manual frame reader, one sim, early events."""
import re

import ira_mod
import numpy as np
from ase import Atoms
from pykmc.utils.geometry import transform_positions

from pylatkmc.ingest.htst.hessian_lammps import compute_mass_weighted_hessian, select_free_atoms
from pylatkmc.ingest.htst.kappa_rpa import vineyard_prefactor
from pylatkmc.ingest.trajectory_recovery import (
    TargetEvent,
    _parse_pykmc_out_fallback,
    detect_movers,
    load_reference_event,
    recover_event_nu0,
    resolve_cadence,
    resolve_potential,
)

KMAX=1.8

def read_frame_fast(path, frame_idx):
    with open(path) as f:
        for _ in range(frame_idx):
            n=int(f.readline()); f.readline()
            for _ in range(n): f.readline()
        n=int(f.readline()); comment=f.readline()
        syms=[]; pos=np.empty((n,3))
        for i in range(n):
            p=f.readline().split(); syms.append(p[0]); pos[i]=[float(p[1]),float(p[2]),float(p[3])]
    m=re.search(r'Lattice="([^"]+)"', comment)
    cell=None
    if m:
        v=[float(x) for x in m.group(1).split()]
        cell=[v[0],v[4],v[8]]  # diagonal of 3x3
    return syms, pos, cell

def unwrap(coords, centre, celld):
    out=coords.copy()
    for k in range(3):
        out[:,k]-=celld[k]*np.round((out[:,k]-centre[k])/celld[k])
    return out

def full_nu0(sim, idx, pot, fr_before):
    ev=load_reference_event(sim, idx)
    cinit=np.asarray(ev["initial_positions"],float); csad=np.asarray(ev["saddle_positions"],float)
    midx=int(ev["move_atom_idx"]); rclu=np.linalg.norm(cinit-cinit[midx],axis=1).max()
    sym0,pos0,celld=read_frame_fast(sim+"/trajkmc.xyz", fr_before)
    sym1,pos1,_=read_frame_fast(sim+"/trajkmc.xyz", fr_before+1)
    f0=Atoms(sym0,positions=pos0,cell=celld,pbc=True); f1=Atoms(sym1,positions=pos1,cell=celld,pbc=True)
    ms=detect_movers(f0,f1)
    if ms is None: return ("no_mover",None)
    mfull=ms.primary
    celld=np.array(celld)
    # neighbourhood within cluster radius (min-image)
    d=pos0-pos0[mfull]; d-=celld*np.round(d/celld); dist=np.linalg.norm(d,axis=1)
    nbr=np.where(dist<=rclu+0.2)[0]
    if abs(len(nbr)-len(cinit))>6: return (f"size({len(nbr)}v{len(cinit)})",None)
    coords1=unwrap(pos0[nbr],pos0[mfull],celld)
    n1,n2=len(coords1),len(cinit)
    try: R,t,perm,dh=ira_mod.IRA().match(n1,['X']*n1,coords1,n2,['X']*n2,cinit,KMAX)
    except Exception as e: return (f"ira:{e}",None)
    perm=np.asarray(perm,int); m=min(n1,len(perm))
    ci=transform_positions(cinit,R,t,perm); cs=transform_positions(csad,R,t,perm)
    rmsd=float(np.sqrt(((ci[:m]-coords1[:m])**2).sum(1).mean()))
    full0=pos0.copy(); fulls=pos0.copy()
    fulls[nbr[:m]]=pos0[nbr[:m]]+(cs[:m]-ci[:m])
    mloc=int(np.argmin(np.linalg.norm(pos0[nbr[:m]]-pos0[mfull],axis=1)))
    freeg=nbr[:m][select_free_atoms(pos0[nbr[:m]],mloc,radius=6.0)]
    try:
        h0=compute_mass_weighted_hessian(full0,sym0,list(celld),freeg,pot,dx=0.01,pbc=True)
        hs=compute_mass_weighted_hessian(fulls,sym0,list(celld),freeg,pot,dx=0.01,pbc=True)
        nu=vineyard_prefactor(h0,hs,n_zero_modes=0)
    except Exception as e: return (f"hess:{str(e)[:50]}",None)
    return ("ok",dict(nu0=nu,nfree=len(freeg),rmsd=rmsd))

sim="/Users/stephenkerr/kmc/Data/Research/100Ni/10vac/T1200/NiAlH_full"
df=_parse_pykmc_out_fallback(sim+"/pykmc.out"); cad=resolve_cadence(sim)
pot=resolve_potential(sim,"auto")
print(f"sim=10vac/T1200 cadence se={cad.sample_every} nframes={cad.n_frames}")
# early fired events (low step -> low frame -> fast read)
seen=set(); done=0
for _,r in df.head(40).iterrows():
    step=int(r["step"]); idx=int(r["ref_event"])
    if idx in seen: continue
    seen.add(idx)
    fb=cad.frame_before_step(step)
    if fb is None: continue
    res=full_nu0(sim,idx,pot,fb)
    if res[0]!="ok":
        print(f"  idx={idx} step={step}: skip ({res[0]})"); continue
    rc=recover_event_nu0(TargetEvent("?","?",sim,idx,0,None),"auto",verify_trajectory=False)
    cl=rc.nu0_Hz/1e12 if rc.nu0_Hz else float('nan')
    fu=res[1]["nu0"]/1e12
    print(f"  idx={idx:3d} step={step:3d}: cluster={cl:5.1f}  FULL={fu:5.1f} THz  ratio={fu/cl:.2f}  align_rmsd={res[1]['rmsd']:.2f} nfree={res[1]['nfree']}")
    done+=1
    if done>=3: break
print("done" if done else "none reconstructable")

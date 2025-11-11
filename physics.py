"""
Physics functions: forces, potentials, energy calculations.
"""
import numpy as np
import math
from numba import njit, prange

# Physical constants in SI units (defined here for numba compatibility)
KB = 1.380649e-23  # Boltzmann constant [J/K]

@njit
def lj_force(r2, epsilon, sigma):
    """
    Compute LJ force magnitude for squared distance r2.
    
    Parameters:
    -----------
    r2 : float
        Squared distance between particles [m²]
    epsilon : float
        LJ energy parameter [J]
    sigma : float
        LJ length parameter [m]
    
    Returns:
    --------
    force_magnitude : float
        Force magnitude [N]
    """
    if r2 <= 1e-20:  # avoid division by zero
        return 0.0
    
    sig2 = sigma * sigma
    sig6 = sig2 * sig2 * sig2
    sig12 = sig6 * sig6
    
    inv_r2 = 1.0 / r2
    inv_r6 = inv_r2 * inv_r2 * inv_r2
    inv_r12 = inv_r6 * inv_r6
    
    # Correct LJ force: F = 24 * epsilon * (2*(sigma^12)/r^13 - (sigma^6)/r^7) / r
    # Simplified: F = 24 * epsilon * (2*sig12*inv_r12 - sig6*inv_r6) * inv_r2
    force_magnitude = 24.0 * epsilon * (2.0 * sig12 * inv_r12 - sig6 * inv_r6) * inv_r2
    
    return force_magnitude

@njit
def lj_potential(r2, epsilon, sigma, cutoff):
    """
    Compute LJ potential with cutoff.
    
    Parameters:
    -----------
    r2 : float
        Squared distance [m²]
    epsilon : float
        LJ energy parameter [J]
    sigma : float
        LJ length parameter [m]
    cutoff : float
        Cutoff distance [m]
    
    Returns:
    --------
    potential : float
        Potential energy [J]
    """
    if r2 >= cutoff * cutoff:
        return 0.0
    
    sig2 = sigma * sigma
    sig6 = sig2 * sig2 * sig2
    sig12 = sig6 * sig6
    
    inv_r2 = 1.0 / r2
    inv_r6 = inv_r2 * inv_r2 * inv_r2
    inv_r12 = inv_r6 * inv_r6
    
    # Calculate potential at cutoff for shifting
    rc2 = cutoff * cutoff
    inv_rc2 = 1.0 / rc2
    inv_rc6 = inv_rc2 * inv_rc2 * inv_rc2
    inv_rc12 = inv_rc6 * inv_rc6
    shift = 4.0 * epsilon * (sig12 * inv_rc12 - sig6 * inv_rc6)
    
    potential = 4.0 * epsilon * (sig12 * inv_r12 - sig6 * inv_r6) - shift
    
    return potential

@njit(parallel=True)
def compute_forces(positions, head, linked, cells_per_side, cell_size, L,
                   cutoff, epsilon, sigma):
    """
    Compute forces using linked-cell neighbor list.
    
    Parameters:
    -----------
    positions : ndarray
        Particle positions [m]
    head, linked : ndarray
        Linked list data structures
    cells_per_side : int
        Number of cells per dimension
    cell_size : float
        Size of each cell [m]
    L : float
        Box size [m]
    cutoff : float
        LJ cutoff distance [m]
    epsilon : float
        LJ energy parameter [J]
    sigma : float
        LJ length parameter [m]
    
    Returns:
    --------
    forces : ndarray
        Forces on particles [N]
    """
    N = positions.shape[0]
    forces = np.zeros((N, 3), dtype=np.float64)
    cutoff2 = cutoff * cutoff
    
    # Iterate over all cells in parallel
    n_cells = cells_per_side * cells_per_side * cells_per_side
    
    for cell_idx in prange(n_cells):
        # Compute cell coordinates
        ix = cell_idx // (cells_per_side * cells_per_side)
        rem = cell_idx % (cells_per_side * cells_per_side)
        iy = rem // cells_per_side
        iz = rem % cells_per_side
        
        # Particles in this cell
        i = head[cell_idx]
        while i != -1:
            pos_i = positions[i]
            
            # Check neighbor cells (including itself)
            for dx in (-1, 0, 1):
                nx = ix + dx
                if nx < 0 or nx >= cells_per_side:
                    continue
                for dy in (-1, 0, 1):
                    ny = iy + dy
                    if ny < 0 or ny >= cells_per_side:
                        continue
                    for dz in (-1, 0, 1):
                        nz = iz + dz
                        if nz < 0 or nz >= cells_per_side:
                            continue
                            
                        neighbor_cell = (nx * cells_per_side * cells_per_side + 
                                       ny * cells_per_side + nz)
                        j = head[neighbor_cell]
                        
                        while j != -1:
                            # Avoid double counting and self-interaction
                            if j > i:
                                dxij = pos_i[0] - positions[j, 0]
                                dyij = pos_i[1] - positions[j, 1]
                                dzij = pos_i[2] - positions[j, 2]
                                
                                # Apply minimum image convention
                                dxij -= L * round(dxij / L)
                                dyij -= L * round(dyij / L)
                                dzij -= L * round(dzij / L)
                                
                                r2 = dxij * dxij + dyij * dyij + dzij * dzij
                                
                                if r2 <= cutoff2 and r2 > 1e-20:
                                    force_mag = lj_force(r2, epsilon, sigma)
                                    
                                    fx = force_mag * dxij
                                    fy = force_mag * dyij
                                    fz = force_mag * dzij
                                    
                                    # Accumulate forces (Newton's 3rd law)
                                    forces[i, 0] += fx
                                    forces[i, 1] += fy
                                    forces[i, 2] += fz
                                    forces[j, 0] -= fx
                                    forces[j, 1] -= fy
                                    forces[j, 2] -= fz
                            
                            j = linked[j]
            i = linked[i]
    
    return forces

@njit
def kinetic_energy(velocities, mass):
    """
    Compute total kinetic energy.
    
    Parameters:
    -----------
    velocities : ndarray
        Particle velocities [m/s]
    mass : float
        Particle mass [kg]
    
    Returns:
    --------
    ke : float
        Total kinetic energy [J]
    """
    ke = 0.0
    for i in range(velocities.shape[0]):
        v2 = (velocities[i, 0]**2 + velocities[i, 1]**2 + velocities[i, 2]**2)
        ke += 0.5 * mass * v2
    return ke

@njit
def temperature_from_ke(ke, N, dof_red=0):
    """
    Compute temperature from kinetic energy.
    
    Parameters:
    -----------
    ke : float
        Kinetic energy [J]
    N : int
        Number of particles
    dof_red : int
        Reduced degrees of freedom (e.g., for constraints)
    
    Returns:
    --------
    temperature : float
        Temperature [K]
    """
    # Use the KB constant defined in this module (numba compatible)
    dof = 3 * N - dof_red
    if dof <= 0:
        return 0.0
    return (2.0 * ke) / (dof * KB)
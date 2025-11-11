"""
Integration methods and boundary conditions.
"""
import numpy as np
import math
from numba import njit

@njit
def apply_reflecting_walls(positions, velocities, L):
    """
    Apply reflecting boundary conditions.
    
    Parameters:
    -----------
    positions : ndarray
        Particle positions [m]
    velocities : ndarray
        Particle velocities [m/s]
    L : float
        Box size [m]
    """
    N = positions.shape[0]
    for i in range(N):
        for d in range(3):
            if positions[i, d] < 0.0:
                positions[i, d] = -positions[i, d]
                velocities[i, d] = -velocities[i, d]
            elif positions[i, d] >= L:
                positions[i, d] = 2.0 * L - positions[i, d]
                velocities[i, d] = -velocities[i, d]

@njit
def apply_periodic_boundaries(positions, L):
    """
    Apply periodic boundary conditions.
    
    Parameters:
    -----------
    positions : ndarray
        Particle positions [m]
    L : float
        Box size [m]
    """
    N = positions.shape[0]
    for i in range(N):
        for d in range(3):
            if positions[i, d] < 0.0:
                positions[i, d] += L
            elif positions[i, d] >= L:
                positions[i, d] -= L

@njit
def velocity_verlet_step(positions, velocities, forces, dt, mass, L, 
                        boundary_type='reflecting'):
    """
    Single Velocity Verlet integration step.
    
    Parameters:
    -----------
    positions : ndarray
        Particle positions [m]
    velocities : ndarray
        Particle velocities [m/s]
    forces : ndarray
        Current forces [N]
    dt : float
        Time step [s]
    mass : float
        Particle mass [kg]
    L : float
        Box size [m]
    boundary_type : str
        'reflecting' or 'periodic'
    """
    N = positions.shape[0]
    
    # Velocity half step
    for i in range(N):
        for d in range(3):
            velocities[i, d] += 0.5 * dt * forces[i, d] / mass
    
    # Position full step
    for i in range(N):
        for d in range(3):
            positions[i, d] += dt * velocities[i, d]
    
    # Apply boundary conditions
    if boundary_type == 'reflecting':
        apply_reflecting_walls(positions, velocities, L)
    else:  # periodic
        apply_periodic_boundaries(positions, L)
    
    # Note: Second velocity half step happens after force calculation
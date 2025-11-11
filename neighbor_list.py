"""
Linked-cell neighbor list implementation.
"""
import numpy as np
import math
from numba import njit

@njit
def build_cell_list(positions, L, cutoff):
    """
    Build linked-cell neighbor list.
    
    Parameters:
    -----------
    positions : ndarray
        Particle positions [m]
    L : float
        Box size [m]
    cutoff : float
        Cutoff distance [m]
    
    Returns:
    --------
    head : ndarray
        Head pointers for cells
    linked : ndarray
        Linked list of particles
    cells_per_side : int
        Number of cells per dimension
    cell_size : float
        Size of each cell [m]
    """
    N = positions.shape[0]
    
    # Ensure at least 1 cell and cell_size >= cutoff
    cells_per_side = max(1, int(math.floor(L / cutoff)))
    cell_size = L / cells_per_side
    
    # Initialize arrays
    n_cells = cells_per_side * cells_per_side * cells_per_side
    head = -1 * np.ones(n_cells, dtype=np.int64)
    linked = -1 * np.ones(N, dtype=np.int64)
    
    # Assign particles to cells
    for i in range(N):
        # Ensure particle is within [0, L)
        x = positions[i, 0] % L
        y = positions[i, 1] % L  
        z = positions[i, 2] % L
        
        cell_x = int(x / cell_size)
        cell_y = int(y / cell_size)
        cell_z = int(z / cell_size)
        
        # Clamp to valid range
        cell_x = min(cells_per_side - 1, max(0, cell_x))
        cell_y = min(cells_per_side - 1, max(0, cell_y))
        cell_z = min(cells_per_side - 1, max(0, cell_z))
        
        cell_idx = (cell_x * cells_per_side * cells_per_side + 
                   cell_y * cells_per_side + cell_z)
        
        # Add to linked list
        linked[i] = head[cell_idx]
        head[cell_idx] = i
    
    return head, linked, cells_per_side, cell_size
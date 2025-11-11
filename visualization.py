"""
Visualization utilities.
"""
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def plot_temperature(time_history, temp_history):
    """
    Plot temperature evolution.
    
    Parameters:
    -----------
    time_history : ndarray
        Time points [s]
    temp_history : ndarray
        Temperature values [K]
    """
    plt.figure(figsize=(10, 6))
    plt.plot(time_history * 1e12, temp_history, 'b-', linewidth=2)
    plt.xlabel('Time [ps]', fontsize=12)
    plt.ylabel('Temperature [K]', fontsize=12)
    plt.title('Temperature Evolution', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

def visualize_snapshots(vis_positions, vis_times, L, max_frames=6):
    """
    Visualize simulation snapshots.
    
    Parameters:
    -----------
    vis_positions : list
        List of position arrays [m]
    vis_times : list
        List of time points [s]
    L : float
        Box size [m]
    max_frames : int
        Maximum number of frames to display
    """
    if len(vis_positions) == 0:
        return
    
    # Select frames to display
    idxs = np.linspace(0, len(vis_positions)-1, 
                      min(max_frames, len(vis_positions))).astype(int)
    
    ncols = len(idxs)
    fig, axes = plt.subplots(1, ncols, figsize=(5*ncols, 5))
    
    if ncols == 1:
        axes = [axes]
    
    for i, idx in enumerate(idxs):
        pos = vis_positions[idx]
        ax = axes[i]
        
        # Convert to nanometers for plotting
        pos_nm = pos * 1e9
        L_nm = L * 1e9
        
        ax.scatter(pos_nm[:, 0], pos_nm[:, 1], s=10, alpha=0.7)
        ax.set_xlim(0, L_nm)
        ax.set_ylim(0, L_nm)
        ax.set_xlabel('x [nm]', fontsize=10)
        ax.set_ylabel('y [nm]', fontsize=10)
        ax.set_title(f't = {vis_times[idx]*1e12:.1f} ps', fontsize=11)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
    
    plt.suptitle('2D Projection Snapshots', fontsize=14)
    plt.tight_layout()
    plt.show()

def plot_energy_evolution(time_history, energy_history, energy_type='Kinetic'):
    """
    Plot energy evolution.
    
    Parameters:
    -----------
    time_history : ndarray
        Time points [s]
    energy_history : ndarray
        Energy values [J]
    energy_type : str
        Type of energy for labeling
    """
    plt.figure(figsize=(10, 6))
    plt.plot(time_history * 1e12, energy_history * 1e21, 'g-', linewidth=2)
    plt.xlabel('Time [ps]', fontsize=12)
    plt.ylabel(f'{energy_type} Energy [zJ]', fontsize=12)
    plt.title(f'{energy_type} Energy Evolution', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
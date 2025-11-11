"""
Main MD simulation script.
"""
import numpy as np
import time
from config import config, KB  # Import KB from config
from physics import compute_forces, kinetic_energy, temperature_from_ke
from neighbor_list import build_cell_list
from integration import velocity_verlet_step, apply_reflecting_walls
from visualization import plot_temperature, visualize_snapshots, plot_energy_evolution

def initialize_positions(N, L, sigma):
    """
    Initialize particle positions on cubic lattice.
    
    Parameters:
    -----------
    N : int
        Number of particles
    L : float
        Box size [m]
    sigma : float
        LJ sigma parameter [m]
    
    Returns:
    --------
    positions : ndarray
        Initial positions [m]
    """
    np.random.seed(config["seed"])
    
    # Determine cubic grid size
    n_side = int(np.ceil(N ** (1 / 3)))
    spacing = L / n_side
    
    positions = np.zeros((N, 3), dtype=np.float64)
    idx = 0
    
    for i in range(n_side):
        for j in range(n_side):
            for k in range(n_side):
                if idx >= N:
                    break
                positions[idx, 0] = (i + 0.5) * spacing
                positions[idx, 1] = (j + 0.5) * spacing
                positions[idx, 2] = (k + 0.5) * spacing
                idx += 1
            if idx >= N:
                break
        if idx >= N:
            break
    
    # Add small random displacements
    positions += (np.random.rand(N, 3) - 0.5) * 0.1 * sigma
    
    return positions

def initialize_velocities(N, T, mass, hot_speed):
    """
    Initialize particle velocities.
    
    Parameters:
    -----------
    N : int
        Number of particles
    T : float
        Temperature [K]
    mass : float
        Particle mass [kg]
    hot_speed : float
        Speed of hot particle [m/s]
    
    Returns:
    --------
    velocities : ndarray
        Initial velocities [m/s]
    hot_idx : int
        Index of hot particle
    """
    # Use KB imported from config
    std = np.sqrt(KB * T / mass)
    velocities = np.random.normal(0.0, std, size=(N, 3))
    
    # Remove net momentum
    v_mean = velocities.mean(axis=0)
    velocities -= v_mean
    
    # Select hot particle
    hot_idx = np.random.randint(0, N)
    direction = np.random.normal(size=3)
    direction /= np.linalg.norm(direction)
    velocities[hot_idx] = direction * hot_speed
    
    return velocities, hot_idx

def run_md(config):
    """
    Main MD simulation function.
    
    Parameters:
    -----------
    config : dict
        Simulation configuration
    
    Returns:
    --------
    results : dict
        Simulation results
    """
    # Extract parameters
    N = config["N"]
    L = config["box_L"]
    dt = config["dt"]
    steps = config["steps"]
    neighbor_update_freq = config["neighbor_update_freq"]
    cutoff = config["cutoff"] * config["sigma"]
    epsilon = config["epsilon"]
    sigma = config["sigma"]
    mass = config["mass"]
    hot_speed = config["hot_particle_speed"]
    T0 = config["initial_temperature"]
    
    # Initialize system
    positions = initialize_positions(N, L, sigma)
    velocities, hot_idx = initialize_velocities(N, T0, mass, hot_speed)
    
    # Build initial neighbor list and compute forces
    head, linked, cells_per_side, cell_size = build_cell_list(positions, L, cutoff)
    forces = compute_forces(positions, head, linked, cells_per_side, cell_size, 
                           L, cutoff, epsilon, sigma)
    
    # Initialize history arrays
    temp_history = []
    time_history = []
    ke_history = []
    vis_positions = []
    vis_times = []
    
    print(f"Starting MD simulation:")
    print(f"  N = {N} particles")
    print(f"  Box size = {L*1e9:.2f} nm")
    print(f"  Time step = {dt*1e15:.1f} fs")
    print(f"  Total time = {steps*dt*1e12:.2f} ps")
    print(f"  Hot particle index: {hot_idx}")
    print(f"  Cutoff distance = {cutoff*1e9:.2f} nm")
    
    start_time = time.time()
    
    # Main MD loop
    for step in range(steps):
        # Velocity Verlet integration
        velocity_verlet_step(positions, velocities, forces, dt, mass, L, 
                           boundary_type='reflecting')
        
        # Rebuild neighbor list if needed
        if step % neighbor_update_freq == 0:
            head, linked, cells_per_side, cell_size = build_cell_list(
                positions, L, cutoff)
        
        # Compute new forces
        forces = compute_forces(positions, head, linked, cells_per_side, 
                               cell_size, L, cutoff, epsilon, sigma)
        
        # Second half of velocity update
        for i in range(N):
            for d in range(3):
                velocities[i, d] += 0.5 * dt * forces[i, d] / mass
        
        # Sampling
        if step % config["sample_temperature_every"] == 0:
            ke = kinetic_energy(velocities, mass)
            temp = temperature_from_ke(ke, N)
            
            temp_history.append(temp)
            ke_history.append(ke)
            time_history.append(step * dt)
        
        # Visualization sampling
        if config["visualize"] and (step % config["vis_every"] == 0):
            if N <= config["vis_max_points"]:
                vis_positions.append(positions.copy())
            else:
                idx = np.random.choice(N, config["vis_max_points"], replace=False)
                vis_positions.append(positions[idx].copy())
            vis_times.append(step * dt)
        
        # Progress reporting
        if (step + 1) % max(1, (steps // 10)) == 0:
            elapsed = time.time() - start_time
            ke_current = kinetic_energy(velocities, mass)
            temp_current = temperature_from_ke(ke_current, N)
            print(f"Step {step+1}/{steps}, Time = {step*dt*1e12:.2f} ps, "
                  f"T = {temp_current:.2f} K, Elapsed = {elapsed:.1f} s")
    
    total_time = time.time() - start_time
    print(f"Simulation completed in {total_time:.2f} seconds")
    print(f"Performance: {steps*N/total_time:.0f} particle-steps/second")
    
    return {
        "positions": positions,
        "velocities": velocities,
        "temp_history": np.array(temp_history),
        "time_history": np.array(time_history),
        "ke_history": np.array(ke_history),
        "vis_positions": vis_positions,
        "vis_times": vis_times,
        "hot_idx": hot_idx
    }

if __name__ == "__main__":
    # Run simulation
    results = run_md(config)
    
    # Plot results
    plot_temperature(results["time_history"], results["temp_history"])
    plot_energy_evolution(results["time_history"], results["ke_history"], "Kinetic")
    
    if config["visualize"]:
        visualize_snapshots(results["vis_positions"], results["vis_times"], 
                          config["box_L"])
    
    print("Simulation completed successfully!")
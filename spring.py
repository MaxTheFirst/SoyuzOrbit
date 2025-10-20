class Spring:
    """
    Представляет одну пружину в цепочке, отслеживая её энергию.
    """

    def __init__(self, spring_constant: float, equilibrium_length: float):
        self.k = spring_constant
        self.equilibrium_length = equilibrium_length
        self.potential_energy = 0.0

    def update_energy(self, pos1: float, pos2: float):
        """
        Рассчитывает и сохраняет потенциальную энергию пружины.
        pos1 и pos2 - координаты объектов на её концах.
        """
        current_length = abs(pos2 - pos1)
        deformation = current_length - self.equilibrium_length
        self.potential_energy = 0.5 * self.k * (deformation ** 2)
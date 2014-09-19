#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@ethz.ch>
# Date:    17.09.2014 10:25:24 CEST
# File:    tb_hamilton.py

import sys
import numpy as np
import sympy as sp

class tb_system:
    """
    """
    def __init__(self, a_1, a_2, a_3):
        self.__unit_cell = [a_1, a_2, a_3]
        for vec in self.__unit_cell:
            if(len(vec) != 3):
                raise ValueError('invalid argument: length of vector != 3')
        self.__atoms = []
        self.__hoppings = []

    def add_atom(self, element, position):
        """
        element: a tuple (orbitals, num_electrons)
            orbitals: orbitals of the element (a list of their energies)
            num_electrons: number of electrons in the atom
        position: position relative to the unit cell (3-entry list)
            the position will be mapped into the unit cell (coordinates
            in [0,1])
        """
        
#------------------------check input------------------------------------#
        if(len(position) != 3):
            raise ValueError('position must be a list/tuple of length 3')
        if(len(element) != 2):
            raise ValueError("bad argument for 'element' input variable")
        if not(isinstance(element[1], int)):
            raise ValueError("num_electrons must be an integer")
            
#--------add the atom - store as (orbitals, num_electrons, position)----#
        self.__atoms.append((tuple(element[0]), element[1], tuple(position)))
#----------------return the index the atom will get---------------------#
        return len(self.__atoms) - 1
        
    def add_hopping(self, overlap, orbital_1, orbital_2, rec_lattice_vec):
        """
        adds an hopping of value 'overlap' between atom_1 and atom_2
        
        orbital_1, orbital_2: tuple (atom_index, orbital_index)
        
        while atom_1 is in the unit cell at the origin, 
        atom_2 is in the unit cell at rec_lattice_vec
        """
#----------------check if the orbitals exist----------------------------#
        num_atoms = len(self.__atoms)
        if not(orbital_1[0] < num_atoms and orbital_2[0] < num_atoms):
            raise ValueError("atom index out of range")
        if not(orbital_1[1] < len(self.__atoms[orbital_1[0]][0])):
            raise ValueError("orbital index out of range (orbital_1)")
        if not(orbital_2[1] < len(self.__atoms[orbital_2[0]][0])):
            raise ValueError("orbital index out of range (orbital_2)")
#----------------check rec_lattice_vec----------------------------------#
        if(len(rec_lattice_vec) != 3):
            raise ValueError('length of rec_lattice_vec must be 3')
        for coord in rec_lattice_vec:
            if not(isinstance(coord, int)):
                raise ValueError('rec_lattice_vec must consist of integers')

#----------------add hopping--------------------------------------------#
        indices_1 = (orbital_1[0], orbital_1[1])
        indices_2 = (orbital_2[0], orbital_2[1])
        connecting_vector = tuple(self.__atoms[orbital_2[0]][2][i] - self.__atoms[orbital_1[0]][2][i] + rec_lattice_vec[i] for i in range(3))
        self.__hoppings.append((overlap, indices_1, indices_2, connecting_vector))
        
    def num_atoms(self):
        return len(self.__atoms)

    def create_hamiltonian(self):
#----------------create conversion from index to orbital/vice versa-----#
        count = 0
        orbital_to_index = []
        index_to_orbital = []
        for atom_num, atom in enumerate(self.__atoms):
            num_orbitals = len(atom[0])
            orbital_to_index.append([count + i for i in range(num_orbitals)])
            for i in range(num_orbitals):
                index_to_orbital.append((atom_num, i))
            count += num_orbitals

        kx, ky, kz = sp.symbols('kx ky kz')
        k = (kx, ky, kz)
        
        H = [list(row) for row in np.diag([energy for atom in self.__atoms for energy in atom[0]])]
        H = sp.sympify(H)
        
        for hopping in self.__hoppings:
            index_1 = orbital_to_index[hopping[1][0]][hopping[1][1]]
            index_2 = orbital_to_index[hopping[2][0]][hopping[2][1]]
            phase = sp.exp(sum([hopping[3][i]*k_comp for i, k_comp in enumerate(k)]))
            H[index_1][index_2] += hopping[0] * phase
            H[index_2][index_1] += (hopping[0] * phase).conjugate()
            
        self.hamiltonian = lambda kxval, kyval, kzval: [[expr.subs([(kx,kxval), (ky, kyval), (kz, kzval)]) for expr in row] for row in H]
        return self.hamiltonian
        
        
    def DEBUG(self):
        print(self.__atoms)
        print(self.__hoppings)
        
if __name__ == "__main__":
    a = tb_system([0.1, 0.2, 0.3],[0.1, 0.3, 0.2],[0.3, 0.2, 0.1])
    a.add_atom(([0.1, 0.1],1),[1,2,3])
    a.add_atom(([0.2, 0.1],1),[1,2,2.2])
    a.add_hopping(1j, (0,1),(1,1),[0,0,1])
    H = a.create_hamiltonian()
    print(H(1,2,3))
    #~ a.DEBUG()

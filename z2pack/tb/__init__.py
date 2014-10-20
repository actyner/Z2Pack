#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@ethz.ch>
# Date:    17.09.2014 10:25:24 CEST
# File:    tb_hamilton.py

from . import vectors

import copy
import numpy as np
import sympy as sp
import scipy.linalg as la

class Hamilton:
    """
    Describes a tight-binding model for use with :class:`z2pack.tb.System`.
    """
    def __init__(self):
        self._atoms = []
        self._hoppings = []
        self._electrons = 0

    def add_atom(self, element, position):
        """
        :param element:     A tuple ``(orbitals, num_electrons)``, where ``orbitals`` is the list of orbital energies and ``num_electrons`` the number of electrons.
        
        :param position:    Position relative to the reciprocal lattice vector
        :type position:     list of length 3
        
        :returns:           Index of the atom
        :rtype:             int
        """
        
        # check input
        if(len(position) != 3):
            raise ValueError('position must be a list/tuple of length 3')
        if(len(element) != 2):
            raise ValueError("bad argument for 'element' input variable")
        if not(isinstance(element[1], int)):
            raise ValueError("num_electrons must be an integer")
            
        # add the atom - store as (orbitals, num_electrons, position)
        self._atoms.append((tuple(element[0]), element[1], tuple(position)))
        # return the index the atom will get
        return len(self._atoms) - 1
        
    def add_hopping(self,  orbital_pairs, rec_lattice_vec, overlap, phase = None):
        """
        Adds a hopping term between orbitals. If the orbitals are not equal, the complex conjugate term is also added.

        :param orbital_pairs:       A tuple ``(orbital_1, orbital_2)``, where ``orbital_*`` is again a tuple ``(atom_index, orbital_index)``. Can also be a list of orbital pairs.
        :param rec_lattice_vec:     Vector connecting unit cells (``list`` of length 3), or list of such vectors
        :param overlap:             Strength of the hopping
        :param phase:               Multiplicative factor for the overlap or a ``list`` of factors (one for each ``rec_lattice_vec``)
        """
        # check if there are multiple orbital pairs
        try:
            orbital_pairs[0][0][0]
            for pair in orbital_pairs:
                self.add_hopping(pair, rec_lattice_vec, overlap, phase)
        except TypeError:
            # check if the orbitals exist
            num_atoms = len(self._atoms)
            if not(orbital_pairs[0][0] < num_atoms and orbital_pairs[1][0] < num_atoms):
                raise ValueError("atom index out of range")
            if not(orbital_pairs[0][1] < len(self._atoms[orbital_pairs[0][0]][0])):
                raise ValueError("orbital index out of range (orbital_pairs[0])")
            if not(orbital_pairs[1][1] < len(self._atoms[orbital_pairs[1][0]][0])):
                raise ValueError("orbital index out of range (orbital_pairs[1])")
                
            # check if there are multiple rec_lattice_vec
            if(hasattr(rec_lattice_vec[0], '__getitem__') and hasattr(rec_lattice_vec[0], '__iter__')):
                if(phase is None):
                    phase = 1
                if(hasattr(phase, '__getitem__') and hasattr(phase, '__iter__')):
                    if(len(phase) == 1):
                        for vec in rec_lattice_vec:
                            self.add_hopping(orbital_pairs, vec, overlap * phase[0])
                    else:
                        for i, vec in enumerate(rec_lattice_vec):
                            self.add_hopping(orbital_pairs, vec, overlap * phase[i])
                else:
                    for vec in rec_lattice_vec:
                        self.add_hopping(orbital_pairs, vec, overlap * phase)
                        
            else:
                # check rec_lattice_vec
                if(len(rec_lattice_vec) != 3):
                    raise ValueError('length of rec_lattice_vec must be 3')
                for coord in rec_lattice_vec:
                    if not(isinstance(coord, int)):
                        raise ValueError('rec_lattice_vec must consist of integers')

                # add hopping
                indices_1 = (orbital_pairs[0][0], orbital_pairs[0][1])
                indices_2 = (orbital_pairs[1][0], orbital_pairs[1][1])
                self._hoppings.append((overlap, indices_1, indices_2, rec_lattice_vec))
    
    def create_hamiltonian(self):
        """
        Creates the ``hamiltonian`` member, which returns the Hamiltonian matrix as a function of k (as a ``list`` of lenth 3).
        
        :returns: ``self.hamiltonian``
        """
        # create conversion from index to orbital/vice versa
        count = 0
        orbital_to_index = []
        index_to_orbital = []
        self._T_list = []
        for atom_num, atom in enumerate(self._atoms):
            num_orbitals = len(atom[0])
            orbital_to_index.append([count + i for i in range(num_orbitals)])
            for i in range(num_orbitals):
                index_to_orbital.append((atom_num, i))
                self._T_list.append(atom[2])
            count += num_orbitals
        
        def _H(k):
            H = [list(row) for row in np.diag([energy for atom in self._atoms for energy in atom[0]])]
            
            for hopping in self._hoppings:
                # add entry for hopping
                index_1 = orbital_to_index[hopping[1][0]][hopping[1][1]]
                index_2 = orbital_to_index[hopping[2][0]][hopping[2][1]]
                phase = np.exp(1j * self._dot_prod(hopping[3], k))
                H[index_1][index_2] += hopping[0] * phase

                # add conjugate if hopping is not on the diagonal
                H[index_2][index_1] += (hopping[0] * phase).conjugate()
            return H
                
        self._num_electrons = sum(atom[1] for atom in self._atoms) # needed for _getM
        self.hamiltonian = _H
        return self.hamiltonian
        
    def _getM(self, string_dir, string_pos, N):
        """
        returns:        M-matrices
        
        args:
        ~~~~
        string_dir:     axis along which string goes (index in 0,1,2)
        string_pos:     position of string as a list where the coord.
                        in string_dir has been removed
        N:              number of steps in the string
        """
        # check if hamiltonian exists - else create it
        try:
            self.hamiltonian
        except (AttributeError, NameError):
            self.create_hamiltonian()
        
        # create k-points for string
        k_points = [copy.copy(string_pos) for i in range(N - 1)]
        ky = np.linspace(0, 1, N - 1, endpoint = False)
        for i, step in enumerate(k_points):
            step.insert(string_dir, ky[i])
            
        # get eigenvectors corr. to occupied states
        eigs = []
        for k in k_points:
            eigval, eigvec = la.eig(self.hamiltonian(k))
            eigval = np.real(eigval)
            idx = eigval.argsort()
            idx = idx[:self._num_electrons]
            idx.sort() # preserve the order of the wcc
            eigvec = eigvec[:,idx]
            eigs.append(np.array(eigvec)) # take only the lower - energy eigenstates

        # last eigenvector = first one
        eigs.append(eigs[0])
        eigsize, eignum = eigs[0].shape
        
        # create M - matrices
        M = []
        deltak = [0, 0]
        deltak.insert(string_dir, 1./(N-1))
        for i in range(0, N - 1):
            Mnew = [[sum(np.conjugate(eigs[i][j,m])*eigs[i + 1][j,n]*np.exp(-1j * self._dot_prod(deltak, self._T_list[j]))  for j in range(eigsize)) for n in range(eignum)] for m in range(eignum)]
            M.append(Mnew) 
        return M
        
    def _dot_prod(self, k_vec, x_vec):
        """
        helper function for dot product of real space with reciprocal space
        vectors (both w.r.t. their basis)
        order or k_vec / x_vec not important
        assumes x_vec / k_vec are w.r.t. the unit cell / reciprocal lattice
            where a_i.b_j = 2*Pi*KroneckerDelta(i,j)
        """
        n = len(k_vec)
        if(len(x_vec) != n):
            raise ValueError('k_vec and x_vec must be of the same size')
        return 2 * np.pi * sum(x_vec[i]*k_vec[i] for i in range(n))
    

#-----------------------------------------------------------------------#
#-----------------------------------------------------------------------#
#                    TIGHT BINDING SPECIALISATION                       #
#-----------------------------------------------------------------------#
#-----------------------------------------------------------------------#

from .. import Z2PackSystem

class System(Z2PackSystem):
    """
    Subclass of Z2PackSystem used for calculating system with a tight-
    binding model
    
    :param tb_hamilton:     system being calculated
    :type tb_hamilton:     :class:`z2pack.tb.Hamilton` object
    :param kwargs:          are passed to the Z2PackPlane constructor via .plane(), which passes them to wcc_calc(), precedence: wcc_calc > plane > this (newer kwargs take precedence)
    """
    def __init__(   self,
                    tb_hamilton,
                    **kwargs
                    ):
        self._defaults = kwargs
        self._tb_hamilton = tb_hamilton
        def _M_handle_creator_tb(string_dir, plane_pos_dir, plane_pos):
            # check if kx is before or after plane_pos_dir
            if(3 - string_dir > 2 * plane_pos_dir):
                return lambda kx, N: self._tb_hamilton._getM(string_dir, [plane_pos, kx], N)
            else:
                return lambda kx, N: self._tb_hamilton._getM(string_dir, [kx, plane_pos], N)
        self._M_handle_creator = _M_handle_creator_tb
        
        
if __name__ == "__main__":
    print("tight_binding.py")
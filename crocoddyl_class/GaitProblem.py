# coding: utf8

import crocoddyl
import numpy as np

# Choose here whiche model : simple or non linear
from crocoddyl_class.ActionModel import *
#from crocoddyl_class.ActionModel_nl import *


class GaitProblem:

    def __init__(self, dt=0.02, nx=12, nu=12, mu=0.8):
        #:param state: state description,
        #:param nu: dimension of control vector,
        #:param nr: dimension of the cost-residual vector (default 1)

        # Time step of the solver
        self.dt = 0.02

        # Period of the MPC
        self.T_mpc = 0.32

        # List of the actionModel
        self.ListAction = []

        # Gait Matrix
        self.gait = np.zeros((6, 5))
        self.fsteps = np.full((6, 13), np.nan)

        # Shooting problem
        self.problem = None

        # Terminal Node
        self.terminalModel = None

        # Max iteration ddp solver
        self.max_iteration = 10

        # ddp
        self.ddp = None

        # Mu, important parameter that need to be changed from the main file
        self.mu = mu

    def createProblem(self):
        for i in range(int(self.T_mpc / self.dt)):
            model = ActionModel(12, 12, self.mu)
            model.createModel()

            # Weight on the state
            model.stateWeight = np.array([1, 1, 150, 35, 30, 8, 20, 20, 15, 4, 4, 8])

            # Weight on the friction cone penalisation
            model.frictionWeight = 10

            # Add model to the list of model
            self.ListAction.append(model)

        # Terminal Model
        self.terminalModel = ActionModel()
        self.terminalModel.createModel()
        # Weight on the friction cone penalisation
        self.terminalModel.stateWeight = np.array([1, 1, 150, 35, 30, 8, 20, 20, 15, 4, 4, 8])
        # No weight on the command for the terminal node
        self.terminalModel.frictionWeight = 0.0

        self.problem = crocoddyl.ShootingProblem(np.zeros(12), self.ListAction, self.terminalModel)
        self.ddp = crocoddyl.SolverDDP(self.problem)

    def updateProblem(self, fsteps, xref, x0):

        self.fsteps = fsteps
        self.createGaitMatrix()

        j = 0
        k_cum = 0
        L = []

        # Iterate over all phases of the gait
        # The first column of xref correspond to the current state
        while (self.gait[j, 0] != 0):
            for i in range(k_cum, k_cum + np.int(self.gait[j, 0])):

                # Update model
                self.ListAction[i].updateModel(np.reshape(self.fsteps[j, 1:], (3, 4), order='F'), xref[:, i + 1],
                                               self.gait[j, 1:])

            k_cum += np.int(self.gait[j, 0])
            j += 1

        # Update model of the terminal model
        self.terminalModel.updateModel(np.reshape(self.fsteps[j - 1, 1:], (3, 4), order='F'), xref[:, -1],
                                       self.gait[j - 1, 1:])

        # update initial state of the problem
        self.problem.x0 = x0

    def createGaitMatrix(self):

        #Construction of the gait matrix representing the feet in contact with the ground
        index = next((idx for idx, val in np.ndenumerate(self.fsteps[:, 0]) if val == 0.0), 0.0)[0]
        self.gait[:, 0] = self.fsteps[:, 0]
        self.gait[:index, 1:] = 1.0 - (np.isnan(self.fsteps[:index, 1::3]) | (self.fsteps[:index, 1::3] == 0.0))

        # Replace NaN values by zeroes
        self.fsteps[np.isnan(self.fsteps)] = 0.0

    def runProblem(self):

        # Not properly warm-started, not needed with simple models
        self.ddp.solve([], [], self.max_iteration)

        return 0

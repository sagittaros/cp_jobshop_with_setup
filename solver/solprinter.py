from ortools.sat.python import cp_model


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, makespan):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0
        self.__makespan = makespan

    def OnSolutionCallback(self):
        print(
            "Solution %i, time = %f s, objective = %i, makespan = %i"
            % (
                self.__solution_count,
                self.WallTime(),
                self.ObjectiveValue(),
                self.Value(self.__makespan),
            )
        )
        self.__solution_count += 1


import collections
from datetime import date, timedelta
from enum import Enum

from ortools.sat.python import cp_model

from .states import index, existing_assignment_index
from .solprinter import SolutionPrinter
from .timeline import export_html


class Objective(Enum):
    SetupTime = "setup_time"
    Transition = "transition"  # implicitly include makespan
    Makespan = "makespan"
    Composite = "composite"


def list_machines(jobs):
    machines_lookup = {}
    for job in jobs:
        for task in job:
            for alt in task:
                machines_lookup[alt.machine_id] = 1
    return list(machines_lookup.keys())


def list_existing_machines(existing):
    machines_lookup = {}
    for assignment in existing:
        machines_lookup[assignment.machine_id] = 1
    return list(machines_lookup.keys())


def compute_horizon(jobs):
    horizon = 0
    for job in jobs:
        for task in job:
            max_task_duration = 0
            for alt in task:
                max_task_duration = max(
                    max_task_duration, alt.processing_time + alt.setup_time
                )
            horizon += max_task_duration
    return horizon


def run_model(jobs, existing, objective_type: Enum, timeline_html: str):
    # Model.
    model = cp_model.CpModel()

    # inputs
    num_jobs = len(jobs)
    all_jobs = range(num_jobs)
    num_existing = len(existing)
    all_existing = range(num_existing)
    machines = set(list_machines(jobs)) | set(list_existing_machines(existing))

    # Compute a maximum makespan greedily.
    horizon = compute_horizon(jobs)
    print("Horizon = %i" % horizon)

    # Global storage of variables.
    intervals_per_machines = collections.defaultdict(list)
    presences_per_machines = collections.defaultdict(list)
    starts_per_machines = collections.defaultdict(list)
    ends_per_machines = collections.defaultdict(list)
    types_per_machines = collections.defaultdict(list)
    setuptimes_per_machines = collections.defaultdict(list)
    ranks_per_machines = collections.defaultdict(list)
    job_starts = {}  # indexed by (job_id, task_id).
    job_presences = {}  # indexed by (job_id, task_id, alt_id).
    job_ranks = {}  # indexed by (job_id, task_id, alt_id).
    job_ends = []  # indexed by job_id

    # Populate variables and intervals
    for job_id in all_jobs:
        job = jobs[job_id]
        num_tasks = len(job)
        previous_start = None
        previous_end = None
        for task_id in range(num_tasks):
            task = job[task_id]
            if len(task) == 0:
                # this can happen if no machine can process the job
                print("no available machines")
                continue

            min_duration = min([alt.processing_time for alt in task])
            max_duration = max([alt.processing_time for alt in task])

            # Create main interval for the task.
            suffix_name = "_j%i_t%i" % (job_id, task_id)
            start = model.NewIntVar(0, horizon, "start" + suffix_name)
            duration = model.NewIntVar(
                min_duration, max_duration, "duration" + suffix_name
            )
            end = model.NewIntVar(0, horizon, "end" + suffix_name)

            # Add precedence constraint
            start_after = task[0].start_after
            if start_after < 0:
                if previous_end:
                    model.Add(start >= previous_end)
            else:
                if previous_start:
                    model.Add(start >= previous_start + start_after)
            previous_start = start
            previous_end = end

            # Store the start for the solution.
            job_starts[(job_id, task_id)] = start

            # Create alternative intervals.
            l_presences = []
            for alt_id, alt in enumerate(task):
                alt_suffix = "_j%i_t%i_a%i" % (job_id, task_id, alt_id)

                domain = cp_model.Domain.FromIntervals(alt.time_domain)
                # create optional interval for machine candidate
                l_presence = model.NewBoolVar("presence" + alt_suffix)
                l_start = model.NewIntVarFromDomain(domain, "start" + alt_suffix)
                l_end = model.NewIntVarFromDomain(domain, "end" + alt_suffix)
                l_duration = alt.processing_time
                l_interval = model.NewOptionalIntervalVar(
                    l_start, l_duration, l_end, l_presence, "interval" + alt_suffix
                )
                l_rank = model.NewIntVar(
                    -1, num_jobs + num_existing, "rank" + alt_suffix
                )
                l_presences.append(l_presence)

                # Link the master variables with the local ones.
                model.Add(start == l_start).OnlyEnforceIf(l_presence)
                model.Add(duration == l_duration).OnlyEnforceIf(l_presence)
                model.Add(end == l_end).OnlyEnforceIf(l_presence)

                # due date constraint
                if alt.due > 0:
                    model.Add(end < alt.due).OnlyEnforceIf(l_presence)

                # Add the local variables to the right machine.
                intervals_per_machines[alt.machine_id].append(l_interval)
                starts_per_machines[alt.machine_id].append(l_start)
                ends_per_machines[alt.machine_id].append(l_end)
                presences_per_machines[alt.machine_id].append(l_presence)
                types_per_machines[alt.machine_id].append(alt.type)
                setuptimes_per_machines[alt.machine_id].append(alt.setup_time)
                ranks_per_machines[alt.machine_id].append(l_rank)

                # Store the variables for the solution.
                job_presences[(job_id, task_id, alt_id)] = l_presence
                job_ranks[(job_id, task_id, alt_id)] = l_rank

            # Only one machine can process each lot.
            model.Add(sum(l_presences) == 1)
        job_ends.append(previous_end)

    for assignment_id in all_existing:
        suffix = "_a%i" % assignment_id
        assignment = existing[assignment_id]
        presence = model.NewConstant(1)
        start = model.NewConstant(assignment.start)
        end = model.NewConstant(assignment.end)
        duration = assignment.end - assignment.start
        interval = model.NewIntervalVar(start, duration, end, "interval" + suffix)
        rank = model.NewIntVar(-1, num_jobs + num_existing, "rank" + suffix)

        # Add local variables to the machine
        intervals_per_machines[assignment.machine_id].append(interval)
        starts_per_machines[assignment.machine_id].append(start)
        ends_per_machines[assignment.machine_id].append(end)
        presences_per_machines[assignment.machine_id].append(presence)
        types_per_machines[assignment.machine_id].append(assignment.type)
        setuptimes_per_machines[assignment.machine_id].append(assignment.setup_time)
        ranks_per_machines[assignment.machine_id].append(rank)

    # Create machines constraints nonoverlap process
    for machine_id in machines:
        intervals = intervals_per_machines[machine_id]
        if len(intervals) > 1:
            model.AddNoOverlap(intervals)

    # Transition times and transition costs using a circuit constraint.
    switch_literals = []
    setup_coeffs = []
    for machine_id in machines:
        machine_starts = starts_per_machines[machine_id]
        machine_ends = ends_per_machines[machine_id]
        machine_presences = presences_per_machines[machine_id]
        machine_types = types_per_machines[machine_id]
        machine_setuptimes = setuptimes_per_machines[machine_id]
        machine_ranks = ranks_per_machines[machine_id]
        arcs = []
        num_machine_tasks = len(machine_starts)
        all_machine_tasks = range(num_machine_tasks)

        for i in all_machine_tasks:
            # Initial arc from the dummy node (0) to a task.
            start_lit = model.NewBoolVar("")
            arcs.append([0, i + 1, start_lit])
            # If this task is the first, set rank and setuptime
            model.Add(machine_ranks[i] == 0).OnlyEnforceIf(start_lit)
            model.Add(machine_starts[i] >= machine_setuptimes[i]).OnlyEnforceIf(
                start_lit
            )
            # Final arc from an arc to the dummy node.
            arcs.append([i + 1, 0, model.NewBoolVar("")])
            # Self arc if the task is not performed.
            arcs.append([i + 1, i + 1, machine_presences[i].Not()])
            model.Add(machine_ranks[i] == -1).OnlyEnforceIf(machine_presences[i].Not())

            for j in all_machine_tasks:
                if i == j:
                    continue

                lit = model.NewBoolVar("%i follows %i" % (j, i))
                arcs.append([i + 1, j + 1, lit])
                model.AddImplication(lit, machine_presences[i])
                model.AddImplication(lit, machine_presences[j])

                # Maintain rank incrementally.
                model.Add(machine_ranks[j] == machine_ranks[i] + 1).OnlyEnforceIf(lit)

                # Compute the transition time if task j is the successor of task i.
                if machine_types[i] != machine_types[j]:
                    switch_literals.append(lit)
                    setup_coeffs.append(machine_setuptimes[j])
                    transition_time = machine_setuptimes[j]
                else:
                    transition_time = 0

                # We add the reified transition to link the literals with the times
                # of the tasks.
                model.Add(
                    machine_starts[j] >= machine_ends[i] + transition_time
                ).OnlyEnforceIf(lit)

        model.AddCircuit(arcs)

    # Objective.
    makespan = model.NewIntVar(0, horizon, "makespan")
    model.AddMaxEquality(makespan, job_ends)

    if objective_type == Objective.SetupTime:
        print("Objective: Minimize setup time")
        model.Minimize(
            sum(
                switch_literals[i] * setup_coeffs[i]
                for i in range(len(switch_literals))
            )
        )
    elif objective_type == Objective.Transition:
        print("Objective: Minimize transition")
        model.Minimize(sum(switch_literals))
    elif objective_type == Objective.Makespan:
        print("Objective: Minimize makespan")
        model.Minimize(makespan)
    else:
        makespan_weight = 1
        transition_weight = 5
        print(
            "Objective: Minimize transitions and makespan with weight %i and %i"
            % (transition_weight, makespan_weight)
        )
        model.Minimize(
            makespan * makespan_weight + sum(switch_literals) * transition_weight
        )

    # Write problem to file.
    with open("problem.proto", "w") as text_file:
        text_file.write(str(model))

    # Solve.
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60 * 60 * 2
    solution_printer = SolutionPrinter(makespan)
    status = solver.SolveWithSolutionCallback(model, solution_printer)

    # Print solution.
    solution = []
    if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
        start = date(2020, 1, 1)
        for job_id in all_jobs:
            for task_id in range(len(jobs[job_id])):
                start_value = solver.Value(job_starts[(job_id, task_id)])
                machine = 0
                product_type = ""
                duration = 0
                select = 0
                rank = -1

                for alt_id in range(len(jobs[job_id][task_id])):
                    if solver.BooleanValue(job_presences[(job_id, task_id, alt_id)]):
                        duration = jobs[job_id][task_id][alt_id].processing_time
                        machine = jobs[job_id][task_id][alt_id].machine_id
                        product_type = jobs[job_id][task_id][alt_id].type
                        select = alt_id
                        rank = solver.Value(job_ranks[(job_id, task_id, alt_id)])
                        end_value = start_value + duration
                        solution.append(
                            {
                                "machine_id": machine,
                                "label": ("j%i: %s" % (job_id, product_type)),
                                "start": start + timedelta(days=start_value),
                                "end": start + timedelta(days=end_value),
                            }
                        )
                        print(
                            "  Job %i starts at %i (alt %i, duration %i) with rank %i on machine %s"
                            % (job_id, start_value, select, duration, rank, machine)
                        )

        for assignment_id in all_existing:
            assignment = existing[assignment_id]
            solution.append(
                {
                    "machine_id": assignment.machine_id,
                    "label": ("existing: %s" % (assignment.type)),
                    "start": start + timedelta(days=assignment.start),
                    "end": start + timedelta(days=assignment.end),
                }
            )
        print("Solve status: %s" % solver.StatusName(status))
        print("Objective value: %i" % solver.ObjectiveValue())
        print("Makespan: %i" % solver.Value(makespan))
        print("Transition: %i" % solver.Value(sum(switch_literals)))
        export_html(solution, timeline_html)
    elif status == cp_model.INFEASIBLE:
        print("INFEASIBLE")


def main():
    jobs = index()
    existing = existing_assignment_index()
    for obj in Objective:
        run_model(jobs, existing, obj, f"{obj}.html")


if __name__ == "__main__":
    main()

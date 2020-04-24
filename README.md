# CP-SAT jobshop scheduler

## Features
- Due date constraints
- Setup time (not sequence dependent but can be modified easily)
- Shifts and breaks (integer domains expressed as intervals)
- Existing assignments as constraints
- Multiple objectives
- Render into gantt chart

## Instruction
```
python -m solver.model
```

## Screenshot
![Alt text](/screenshot.png?raw=true)

## Dependencies
* ortools
* gviz_api

## Modified from
[scheduling_with_transitions_sat.py](https://github.com/google/or-tools/blob/stable/examples/contrib/scheduling_with_transitions_sat.py)

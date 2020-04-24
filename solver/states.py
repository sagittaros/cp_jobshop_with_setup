import collections

# 2 product types P1 and P2
# 5 machines CP1, CP2, DP1, DP2, PK1 (human)
# 2 sales items J1 and J2 of the kind P1
# 2 sales items J3 and J4 of the kind P2
# time is in hours
def index():
    alt = collections.namedtuple(
        "alt",
        [
            "machine_id",
            "type",
            "processing_time",
            "setup_time",
            "due",  # if -1, treat as no due date
            "time_domain",
            "start_after",
        ],
    )

    # in reality, each machine can have different shift period
    domain1 = [(0, 6), (8, 14), (16, 22), (24, 30)]
    domain2 = [(2, 8), (10, 16), (18, 24), (26, 32)]

    """
    start_value for start_type="day"
    task[i].start >= task[i-1].start + start_after
    if value == -1, we will treat start_type=None
    """
    start_after = -1
    return [
        [
            [
                alt("CP1", "P1", 3, 1, 20, domain1, start_after),
                alt("CP2", "P1", 4, 1, 20, domain1, start_after),
            ],  # task 1
            [
                alt("DP1", "P1", 4, 4, 20, domain1, start_after),
                alt("DP2", "P1", 6, 3, 20, domain1, start_after),
            ],  # task 2
            [alt("PK1", "P1", 2, 0, 20, domain1, start_after)],  # task 3
        ],  # job 1
        [
            [
                alt("CP1", "P1", 3, 1, 21, domain1, start_after),
                alt("CP2", "P1", 4, 1, 21, domain1, start_after),
            ],  # task 1
            [
                alt("DP1", "P1", 4, 4, 21, domain1, start_after),
                alt("DP2", "P1", 6, 3, 21, domain1, start_after),
            ],  # task 2
            [alt("PK1", "P1", 2, 0, 21, domain1, start_after)],  # task 3
        ],  # job 2
        [
            [
                alt("CP1", "P1", 3, 1, 100, domain1, start_after),
                alt("CP2", "P1", 4, 1, 100, domain1, start_after),
            ],  # task 1
            [
                alt("DP1", "P1", 4, 4, 100, domain1, start_after),
                alt("DP2", "P1", 6, 3, 100, domain1, start_after),
            ],  # task 2
            [alt("PK1", "P1", 2, 0, 100, domain1, start_after)],  # task 3
        ],  # job 2
        [
            [
                alt("CP1", "P2", 3, 1, 22, domain1, start_after),
                alt("CP2", "P2", 4, 1, 22, domain1, start_after),
            ],  # task 1
            [
                alt("DP1", "P2", 4, 4, 22, domain1, start_after),
                alt("DP2", "P2", 6, 3, 22, domain1, start_after),
            ],  # task 2
            [alt("PK1", "P2", 2, 0, 22, domain1, start_after)],  # task 3
        ],  # job 3
        [
            [
                alt("CP1", "P2", 3, 1, 16, domain2, start_after),
                alt("CP2", "P2", 4, 1, 16, domain2, start_after),
            ],  # task 1
            [
                alt("DP1", "P2", 4, 4, 16, domain2, start_after),
                alt("DP2", "P2", 6, 3, 16, domain2, start_after),
            ],  # task 2
            [alt("PK1", "P2", 2, 0, 16, domain2, start_after)],  # task 3
        ],  # job 4
        [
            [
                alt("CP1", "P2", 3, 1, 100, domain2, start_after),
                alt("CP2", "P2", 4, 1, 100, domain2, start_after),
            ],  # task 1
            [
                alt("DP1", "P2", 4, 4, 100, domain2, start_after),
                alt("DP2", "P2", 6, 3, 100, domain2, start_after),
            ],  # task 2
            [alt("PK1", "P2", 2, 0, 100, domain2, start_after)],  # task 3
        ],  # job 4
        [
            [
                alt("CP1", "P2", 3, 1, 100, domain2, start_after),
                alt("CP2", "P2", 4, 1, 100, domain2, start_after),
            ],  # task 1
            [
                alt("DP1", "P2", 4, 4, 100, domain2, start_after),
                alt("DP2", "P2", 6, 3, 100, domain2, start_after),
            ],  # task 2
            [alt("PK1", "P2", 2, 0, 100, domain2, start_after)],  # task 3
        ],  # job 4
    ]

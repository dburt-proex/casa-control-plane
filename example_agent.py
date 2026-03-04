from CASA.middleware import casa_guard


def database_write():
    print("Writing to database...")


def run():

    actions = [
        ("read_database", lambda: print("Reading database")),
        ("write_database", database_write),
        ("delete_database", lambda: print("Deleting database"))
    ]

    for action_name, tool in actions:

        casa_guard("agent_01", action_name, tool)

        casa_guard("agent_01", action_name, tool)
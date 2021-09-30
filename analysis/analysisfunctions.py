import tables

def generate_groupname_list(faultgroup):
    """
    Generator to get names of all childs in faultgroup
    """
    for node in faultgroup._f_itter_nodes('Group'):
        yield node._v_name

def findout_endstatus_stat(faultgroup, interestlist=None):
    """
    Sort all Experiments into reached end point (success) or not (failed).
    """
    success = []
    failed = []
    if interestlist is None:
        interestlist = generate_groupname_list(faultgroup)

    for nodename in interestlist:
        node = faultgroup._f_get_child(nodename)
        if node.faults.attrs.endpoint == 0:
            failed.append(node._v_name)
        else:
            success.append(node._v_name)
    return [success, failed]

# 0 memory fault
# 1 instruction fault
# 2 register fault 
def findout_experiment_type(faultgroup, faulttype, interestlist=None):
    """
    Filters for a specific fault type. If interestlist is given only experiments in this list will be analysed.
    """
    groupnames = []
    if not isinstance(faulttype, int):
        if "memory" in faulttype:
            faulttype = 0
        elif "instruction" in faulttype:
            faulttype = 1
        elif "register" in faulttype:
            faulttype = 2
        else:
            raise ValueError("Faulttype not known")

    if interestlist is None:
        interestlist = generate_groupname_list(faultgroup)

    for nodename in interestlist:
        node = faultgroup._f_get_child(nodename)
        table = node.faults
        for row in table.iterrows():
            if row['fault_type'] == faulttype:
                groupnames.append(node._v_name)
    return groupnames

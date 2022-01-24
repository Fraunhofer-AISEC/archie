import resource


def gather_process_ram_usage(queue_ram_usage, max_ram_usage):
    process_ram_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    if queue_ram_usage is not None:
        queue_ram_usage.put(process_ram_usage)

    if process_ram_usage > max_ram_usage:
        max_ram_usage = process_ram_usage

    return max_ram_usage

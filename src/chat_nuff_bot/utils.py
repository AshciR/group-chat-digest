def str_to_bool(value):
    """Convert a string representation of truth to a boolean."""
    if isinstance(value, bool):
        return value
    if value.lower() in ('true', 't', '1', 'yes', 'y'):
        return True
    elif value.lower() in ('false', 'f', '0', 'no', 'n'):
        return False
    else:
        raise ValueError(f"Boolean value expected, got '{value}' instead.")
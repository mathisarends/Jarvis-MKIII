def singleton(cls):
    """
    A decorator that transforms a class into a singleton.
    The decorator ensures that only one instance of the class exists.
    """
    instances = {}
    
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance
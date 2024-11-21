from math import sqrt

def calculate_distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points."""
    return sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

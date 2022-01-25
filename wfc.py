from __future__ import print_function

import dimod
import math
import sys
import copy

from dimod.generators.constraints import combinations
from hybrid.reference import KerberosSampler

def get_label(row, col, digit):
    """Returns a string of the cell coordinates and the cell value in a
    standard format.
    """
    return "{row},{col}_{digit}".format(**locals())

def get_matrix(filename):
    """Return a list of lists containing the content of the input text file.

    Note: each line of the text file corresponds to a list. Each item in
    the list is from splitting the line of text by the whitespace ' '.
    """
    with open(filename, "r") as f:
        content = f.readlines()

    lines = []
    for line in content:
        new_line = line.rstrip()    # Strip any whitespace after last value

        if new_line:
            new_line = list(map(int, new_line.split(' ')))
            lines.append(new_line)

    return lines

def build_bqm(matrix):
    """Build BQM using WFC constraints"""
    # Set up
    n = len(matrix)          # Number of rows/columns in matrix
    m = int(math.sqrt(n))    # Number of rows/columns in matrix subsquare
    digits = range(2)

    bqm = dimod.BinaryQuadraticModel({}, {}, 0.0, dimod.SPIN)
    
    # Constraint: Each node can only select one digit
    for row in range(n):
        for col in range(n):
            node_digits = [get_label(row, col, digit) for digit in digits]
            one_digit_bqm = combinations(node_digits, 1)
            bqm.update(one_digit_bqm)

    # Constraint: Each sub-square must match a subsquare of the input
    # Build indices of a basic subsquare
    subsquare_indices = [(row, col) for row in range(m) for col in range(m)]

    # Build full array
    for r_scalar in range(m):
        for c_scalar in range(m):
                # Shifts for moving subsquare inside matrix
                row_shift = r_scalar * m
                col_shift = c_scalar * m
                # Build the labels for a subsquare
                subsquare = [get_label(row + row_shift, col + col_shift, matrix[row + row_shift][col + col_shift])
                             for row, col in subsquare_indices]
                #print(subsquare)
                subsquare_bqm = combinations(subsquare, n)
                bqm.update(subsquare_bqm)

    # Constraint: The output matrix should not be equal to the raw input
    #fullmatrix = [get_label(row, col, matrix[row][col]) for row in range(n) for col in range(n)]
    #print(fullmatrix)
    #matrix_bqm = combinations(fullmatrix, 0)
    #bqm.update(matrix_bqm)

    return bqm

def solve_wfc(bqm, matrix):
    """Solve BQM and return matrix with solution."""
    solution = KerberosSampler().sample(bqm,
                                        max_iter=10,
                                        convergence=3,
                                        qpu_params={'label': 'WFC'})
    best_solution = solution.first.sample
    solution_list = [k for k, v in best_solution.items() if v == 1]

    result = copy.deepcopy(matrix)

    for label in solution_list:
        coord, digit = label.split('_')
        row, col = map(int, coord.split(','))

        #if result[row][col] > 0:
            # the returned solution is not optimal and either tried to
            # overwrite one of the starting values, or returned more than
            # one value for the position. In either case the solution is
            # likely incorrect.
        #    continue

        result[row][col] = int(digit)

    return result

if __name__ == "__main__":
    # Read user input
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "problem.txt"
        print("Warning: using default problem file, '{}'. Usage: python "
              "{} <sudoku filepath>".format(filename, sys.argv[0]))

    # Read sudoku problem as matrix
    matrix = get_matrix(filename)

    # Solve BQM and update matrix
    bqm = build_bqm(matrix)
    result = solve_wfc(bqm, matrix)

    # Print solution
    for line in result:
        print(*line, sep=" ")   # Print list without commas or brackets
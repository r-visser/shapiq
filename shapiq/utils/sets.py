"""This module contains utility functions for dealing with sets, coalitions and game theory."""
import copy
from itertools import chain, combinations
from typing import Iterable, Any, Optional

import numpy as np
from scipy.special import binom


__all__ = [
    "powerset",
    "pair_subset_sizes",
    "split_subsets_budget",
]


def powerset(
    iterable: Iterable[Any], min_size: Optional[int] = 0, max_size: Optional[int] = None
) -> Iterable[tuple]:
    """Return a powerset of an iterable as tuples with optional size limits.

    Args:
        iterable: Iterable.
        min_size: Minimum size of the subsets. Defaults to 0 (start with the empty set).
        max_size: Maximum size of the subsets. Defaults to None (all possible sizes).

    Returns:
        iterable: Powerset of the iterable.

    Example:
        >>> list(powerset([1, 2, 3]))
        [(), (1,), (2,), (3,), (1, 2), (1, 3), (2, 3), (1, 2, 3)]

        >>> list(powerset([1, 2, 3], min_size=1))
        [(1,), (2,), (3,), (1, 2), (1, 3), (2, 3), (1, 2, 3)]

        >>> list(powerset([1, 2, 3], max_size=2))
        [(), (1,), (2,), (3,), (1, 2), (1, 3), (2, 3)]
    """
    s = list(iterable)
    max_size = len(s) if max_size is None else min(max_size, len(s))
    return chain.from_iterable(combinations(s, r) for r in range(max(min_size, 0), max_size + 1))


def pair_subset_sizes(order: int, n: int) -> tuple[list[tuple[int, int]], Optional[int]]:
    """Determines what subset sizes are paired together.

    Given an interaction order and the number of players, determines the paired subsets. Paired
    subsets are subsets of the same size that are paired together moving from the smallest subset
    paired with the largest subset to the center.

    Args:
        order: interaction order.
        n: number of players.

    Returns:
        paired and unpaired subsets. If there is no unpaired subset `unpaired_subset` is None.

    Examples:
        >>> pair_subset_sizes(order=1, n=5)
        ([(1, 4), (2, 3)], None)

        >>> pair_subset_sizes(order=1, n=6)
        ([(1, 5), (2, 4)], 3)

        >>> pair_subset_sizes(order=2, n=5)
        ([(2, 3)], None)
    """
    subset_sizes = list(range(order, n - order + 1))
    n_paired_subsets = len(subset_sizes) // 2
    paired_subsets = [
        (subset_sizes[size - 1], subset_sizes[-size]) for size in range(1, n_paired_subsets + 1)
    ]
    unpaired_subset = None if len(subset_sizes) % 2 == 0 else subset_sizes[n_paired_subsets]
    return paired_subsets, unpaired_subset


def split_subsets_budget(order: int, n: int, budget: int, q: np.ndarray) -> tuple[list, list, int]:
    """Determines which subset sizes can be computed explicitly and which sizes need to be sampled.

    Given a computational budget, determines the complete subsets that can be computed explicitly
    and the corresponding incomplete subsets that need to be estimated via sampling.

    Args:
        order: interaction order.
        n: number of players.
        budget: total allowed budget for the computation.
        q: weight vector of the sampling distribution in shape (n + 1,). The first and last element
            constituting the empty and full subsets are not used.

    Returns:
        complete subsets, incomplete subsets, remaining budget

    Examples:
        >>> split_subsets_budget(order=1, n=6, budget=100, q=np.ones(shape=(6,)))
        ([1, 5, 2, 4, 3], [], 38)

        >>> split_subsets_budget(order=1, n=6, budget=60, q=np.ones(shape=(6,)))
        ([1, 5, 2, 4], [3], 18)

        >>> split_subsets_budget(order=1, n=6, budget=100, q=np.zeros(shape=(6,)))
        ([], [1, 2, 3, 4, 5], 100)
    """
    # determine paired and unpaired subsets
    complete_subsets = []
    paired_subsets, unpaired_subset = pair_subset_sizes(order, n)
    incomplete_subsets = list(range(order, n - order + 1))

    # turn weight vector into probability vector
    weight_vector = copy.copy(q)
    weight_vector[0], weight_vector[-1] = 0, 0  # zero out the empty and full subsets
    sum_weight_vector = np.sum(weight_vector)
    weight_vector = np.divide(
        weight_vector, sum_weight_vector, out=weight_vector, where=sum_weight_vector != 0
    )

    # check if the budget is sufficient to compute all paired subset sizes explicitly
    allowed_budget = weight_vector * budget  # allowed budget for each subset size
    for subset_size_1, subset_size_2 in paired_subsets:
        subset_budget = int(binom(n, subset_size_1))  # required budget for full computation
        # check if the budget is sufficient to compute the paired subset sizes explicitly
        if allowed_budget[subset_size_1] >= subset_budget and allowed_budget[subset_size_1] > 0:
            complete_subsets.extend((subset_size_1, subset_size_2))
            incomplete_subsets.remove(subset_size_1)
            incomplete_subsets.remove(subset_size_2)
            weight_vector[subset_size_1], weight_vector[subset_size_2] = 0, 0  # zero used sizes
            if not np.sum(weight_vector) == 0:
                weight_vector /= np.sum(weight_vector)  # re-normalize into probability vector
            budget -= subset_budget * 2
        else:  # if the budget is not sufficient, return the current state
            return complete_subsets, incomplete_subsets, budget
        allowed_budget = weight_vector * budget  # update allowed budget for each subset size

    # check if the budget is sufficient to compute the unpaired subset size explicitly
    if unpaired_subset is not None:
        subset_budget = int(binom(n, unpaired_subset))
        if budget - subset_budget >= 0:
            complete_subsets.append(unpaired_subset)
            incomplete_subsets.remove(unpaired_subset)
            budget -= subset_budget
    return complete_subsets, incomplete_subsets, budget
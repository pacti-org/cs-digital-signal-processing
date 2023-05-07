from functools import wraps
from typing import Dict, List, Tuple
from pacti.terms.polyhedra import PolyhedralContract

import functools
import dataclasses


@functools.total_ordering
@dataclasses.dataclass
class PolyhedralContractSize:
    # The count of assumptions and guarantees.
    constraints: int = 0

    # The count of input and output variables.
    variables: int = 0

    def __init__(self, contract: PolyhedralContract | None):
        if contract:
            self.constraints = len(contract.a.terms) + len(contract.g.terms)
            self.variables = len(contract.vars)
        else:
            self.constraints = 0
            self.variables = 0

    def __eq__(self, other: "PolyhedralContractSize") -> bool:
        return (self.constraints == other.constraints) and (self.variables == other.variables)

    def __ge__(self, other: "PolyhedralContractSize") -> bool:
        return (self.constraints, self.variables) >= (other.constraints, other.variables)

    def max(self, other: "PolyhedralContractSize") -> "PolyhedralContractSize":
        if self >= other:
            return self
        else:
            return other
        
    def __str__(self) -> str:
        return f"(constraints: {self.constraints}, variables: {self.variables})"


def statistics_decorator(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        wrapper.counter += 1

        # Call the original method to get the resulting contract
        result_contract = fn(*args, **kwargs)

        # Calculate the size of the input contracts and the result contract
        input_size1 = PolyhedralContractSize(contract=args[0])
        input_size2 = PolyhedralContractSize(contract=args[1])
        result_size = PolyhedralContractSize(contract=result_contract)

        # Update the maximum polyhedral contract size if necessary
        wrapper.max_size = max(wrapper.max_size, input_size1, input_size2, result_size)

        # Return the composed contract
        return result_contract

    wrapper.counter = 0
    wrapper.max_size = PolyhedralContractSize(contract=None)
    return wrapper


PolyhedralContract.compose = statistics_decorator(PolyhedralContract.compose)
PolyhedralContract.quotient = statistics_decorator(PolyhedralContract.quotient)
PolyhedralContract.merge = statistics_decorator(PolyhedralContract.merge)


@dataclasses.dataclass
class PolyhedralContractCounts:
    compose_count: int = 0
    quotient_count: int = 0
    merge_count: int = 0

    compose_max_size: PolyhedralContractSize = dataclasses.field(default_factory=lambda: PolyhedralContractSize(contract=None))
    quotient_max_size: PolyhedralContractSize = dataclasses.field(default_factory=lambda: PolyhedralContractSize(contract=None))
    merge_max_size: PolyhedralContractSize = dataclasses.field(default_factory=lambda: PolyhedralContractSize(contract=None))

    def update_counts(self) -> "PolyhedralContractCounts":
        self.compose_count = PolyhedralContract.compose.counter
        self.quotient_count = PolyhedralContract.quotient.counter
        self.merge_count = PolyhedralContract.merge.counter

        self.compose_max_size = PolyhedralContract.compose.max_size
        self.quotient_max_size = PolyhedralContract.quotient.max_size
        self.merge_max_size = PolyhedralContract.merge.max_size

        return self

    def __add__(self, other: "PolyhedralContractCounts") -> "PolyhedralContractCounts":
        result = PolyhedralContractCounts()
        result.compose_count = self.compose_count + other.compose_count
        result.quotient_count = self.quotient_count + other.quotient_count
        result.merge_count = self.merge_count + other.merge_count

        result.compose_max_size = max(self.compose_max_size, other.compose_max_size)
        result.quotient_max_size = max(self.quotient_max_size, other.quotient_max_size)
        result.merge_max_size = max(self.merge_max_size, other.merge_max_size)

        return result

    def __str__(self) -> str:
        return (
            f"PolyhedralContract operation counts: compose={self.compose}, quotient={self.quotient}, merge={self.merge}.\n"
            + f"max sizes for compose={self.compose_max_size}\n"
            + f"max sizes for quotient={self.quotient_max_size}\n"
            + f"max sizes for merge={self.merge_max_size}\n"
        )


@dataclasses.dataclass
class PolyhedralContractCountStats:
    min_compose: int = 0
    min_quotient: int = 0
    min_merge: int = 0

    max_compose: int = 0
    max_quotient: int = 0
    max_merge: int = 0

    avg_compose: float = 0
    avg_quotient: float = 0
    avg_merge: float = 0

    compose_max_size: PolyhedralContractSize = dataclasses.field(default_factory=lambda: PolyhedralContractSize(contract=None))
    quotient_max_size: PolyhedralContractSize = dataclasses.field(default_factory=lambda: PolyhedralContractSize(contract=None))
    merge_max_size: PolyhedralContractSize = dataclasses.field(default_factory=lambda: PolyhedralContractSize(contract=None))

    def stats(self) -> str:
        return ("Pacti compose,quotient,merge statistics:\n"
            + f"min: (compose: {self.min_compose}, quotient: {self.min_quotient}, merge: {self.min_merge})\n"
            + f"max: (compose: {self.max_compose}, quotient: {self.max_quotient}, merge: {self.max_merge})\n"
            + f"avg: (compose: {self.avg_compose}, quotient: {self.avg_quotient}, merge: {self.avg_merge})\n"
            + f"max compose size: {self.compose_max_size}\n"
            + f"max quotient size: {self.quotient_max_size}\n"
            + f"max merge size: {self.merge_max_size}\n"
        )


def polyhedral_count_stats(counts: List[PolyhedralContractCounts]) -> PolyhedralContractCountStats:
    stats = PolyhedralContractCountStats()
    # Minimum counts
    stats.min_compose = min(count.compose_count for count in counts)
    stats.min_quotient = min(count.quotient_count for count in counts)
    stats.min_merge = min(count.merge_count for count in counts)

    # Maximum counts
    stats.max_compose = max(count.compose_count for count in counts)
    stats.max_quotient = max(count.quotient_count for count in counts)
    stats.max_merge = max(count.merge_count for count in counts)

    # Average counts
    n = len(counts)
    stats.avg_compose: float = sum(count.compose_count for count in counts) / n
    stats.avg_quotient: float = sum(count.quotient_count for count in counts) / n
    stats.avg_merge: float = sum(count.merge_count for count in counts) / n

    # Maximum PolyhedralContractSize for each operation
    stats.compose_max_size = max(count.compose_max_size for count in counts)
    stats.quotient_max_size = max(count.quotient_max_size for count in counts)
    stats.merge_max_size = max(count.merge_max_size for count in counts)

    return stats

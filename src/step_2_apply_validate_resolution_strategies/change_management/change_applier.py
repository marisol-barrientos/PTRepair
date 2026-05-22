import copy

from utils.sanity_checks import sanitize_process
from validators.structural_validator import StructuralValidator


class ChangeApplier:

    def __init__(self):

        self.validators = [
            StructuralValidator()
        ]

    def apply(
        self,
        root,
        operation,
        *args,
        **kwargs
    ):

        # -----------------------------------------
        # work on deep copy
        # -----------------------------------------

        candidate = copy.deepcopy(root)

        # -----------------------------------------
        # apply operation
        # -----------------------------------------

        log = operation(
            candidate,
            *args,
            **kwargs
        )

        # -----------------------------------------
        # sanitize
        # -----------------------------------------

        sanitize_process(candidate)

        # -----------------------------------------
        # validate
        # -----------------------------------------

        for validator in self.validators:
            validator.validate(candidate)

        # -----------------------------------------
        # commit only if valid
        # -----------------------------------------

        return candidate, log
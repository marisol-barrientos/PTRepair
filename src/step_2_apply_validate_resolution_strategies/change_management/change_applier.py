import copy

try:
    from ...utils.sanity_checks import sanitize_process
    from ..validators.structural_validator import StructuralValidator
except ImportError as error:
    if "attempted relative import" not in str(error):
        raise

    from src.utils.sanity_checks import sanitize_process
    from src.step_2_apply_validate_resolution_strategies.validators.structural_validator import (
        StructuralValidator,
    )


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
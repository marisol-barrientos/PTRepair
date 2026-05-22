from change_operations.operations import *


class ChangeOperationValidator:

    """
    Validates whether a proposed change operation
    conforms to the predefined set of allowed
    change operations supported by the framework.
    """

    def __init__(self):

        self.allowed_change_operations = {

            insert_after,
            insert_before,
            delete,
            rename,
            move_after,
            move_before,
            swap,
            merge_by_label,
            split,

            modify_condition,

            copy_after,
            copy_before,

            modify_resource,
            modify_write,
            add_write,
            remove_write,
            modify_read,

            parallelize,
            sequentialize_parallel,

            add_xor_branch,
            remove_branch,
            remove_branch_by_condition,

            embed_activity_in_xor,
            embed_pre_loop,
            embed_post_loop,

            remove_loop,
            modify_loop_condition,
            modify_timeout
        }

    def validate(self, operation):

        if operation not in self.allowed_change_operations:

            raise ValueError(
                f"Unsupported change operation: "
                f"{operation.__name__}"
            )

        return True
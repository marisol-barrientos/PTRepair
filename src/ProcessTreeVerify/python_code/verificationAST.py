#    Copyright (C) <2025>  <Johannes Löbbecke>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.



import ast
import logging
from annotated_verification import *

VERIFICATION_FUNCTIONS = {
    "exists": exists,
    "absence": absence,
    "leads_to": leads_to,
    "precedence": precedence,
    "leads_to_absence": leads_to_absence,
    "precedence_absence": precedence_absence,
    "parallel": parallel,
    "executed_by": executed_by,
    "executed_by_identify": executed_by_identify,
    "executed_by_return": executed_by_return,
    "directly_follows": directly_follows,
    "send_exist": send_exist,
    "receive_exist": receive_exist,
    "activity_sends": activity_sends,
    "activity_receives": activity_receives,
    "min_time_between": min_time_between,
    "by_due_date_annotated": by_due_date_annotated,
    "by_due_date_explicit": by_due_date_explicit,
    "by_due_date": by_due_date,
    "recurring": recurring,
    "max_time_between": max_time_between,
    "data_value_alternative": condition,
    "data_value_alternative_directly_follows": condition_directly_follows,
    "data_value_alternative_eventually_follows": condition_eventually_follows,
    "condition": condition,
    "condition_directly_follows": condition_directly_follows,
    "condition_eventually_follows": condition_eventually_follows,
    "data_leads_to_absence": data_leads_to_absence,
    "loop": loop,
    "timed_alternative": timed_alternative,
    "failure_directly_follows": failure_directly_follows,
    "failure_eventually_follows": failure_eventually_follows,
    "exclusive": exclusive,
}

logger = logging.getLogger(__name__)

class MethodValidator(ast.NodeVisitor):

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            allowed = (
                node.func.id in VERIFICATION_FUNCTIONS
                or node.func.id in ["all", "any"]
            )
            if not allowed:
                raise ValueError(
                    f"Function {node.func.id} is not allowed!"
                )
        else:
            raise ValueError(
                "Only direct function calls are allowed!"
            )
        self.generic_visit(node)

    def visit_Attribute(self, node):
        raise ValueError(
            "Attribute access is not allowed!"
        )

    def visit_Name(self, node):
        pass

    def visit_Expr(self, node):
        self.generic_visit(node)

    def visit_Module(self, node):
        if len(node.body) != 1:
            raise ValueError(
                "Only a single expression is allowed!"
            )
        self.generic_visit(node)

class ForceBooleanEvaluation(ast.NodeTransformer):

    def visit_BoolOp(self, node):
        self.generic_visit(node)

        if isinstance(node.op, ast.And):
            return ast.Call(
                func=ast.Name(
                    id='all',
                    ctx=ast.Load()
                ),
                args=[
                    ast.List(
                        elts=node.values,
                        ctx=ast.Load()
                    )
                ],
                keywords=[]
            )

        elif isinstance(node.op, ast.Or):
            return ast.Call(
                func=ast.Name(
                    id='any',
                    ctx=ast.Load()
                ),
                args=[
                    ast.List(
                        elts=node.values,
                        ctx=ast.Load()
                    )
                ],
                keywords=[]
            )

        return node

def verify(expression, **kwargs):

    eval_tree = ast.parse(
        expression,
        mode="eval"
    )

    validator = MethodValidator()
    validator.visit(eval_tree)

    eval_tree = ForceBooleanEvaluation().visit(
        eval_tree
    )

    ast.fix_missing_locations(eval_tree)

    exec_env = VERIFICATION_FUNCTIONS.copy()
    exec_env.update(kwargs)

    exec_env["all"] = all
    exec_env["any"] = any

    evaluation = eval(
        compile(
            eval_tree,
            filename="<ast>",
            mode="eval"
        ),
        {"__builtins__": None},
        exec_env
    )

    assurance_level = logger.get_assurance_level()

    return evaluation, assurance_level
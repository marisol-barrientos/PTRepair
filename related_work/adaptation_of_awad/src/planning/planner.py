from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.context.business_context import BusinessContext
from src.model.node import Node, NodeType
from src.model.pst import ProcessStructureTree


@dataclass
class FastDownwardConfig:
    """
    Minimal config to call Fast Downward as an external process.
    """
    fd_path: str = "planners/fast-downward/fast-downward.py"  # path to fast-downward.py OR folder
    python_exe: str = "python3"
    alias: str = "lama-first"
    work_dir: str = "./fd_work"
    plan_file: str = "sas_plan"
    timeout_sec: int = 30           # hard timeout per call
    keep_output: bool = True        # write fd_stdout.txt for debugging


class Planner:
    """
    Python equivalent of Java Planner, but using Fast Downward.

    API:
        find_plan(init_state: List[str], final_state: List[str]) -> Optional[ProcessStructureTree]
    """

    def __init__(self, bc: BusinessContext, config: FastDownwardConfig):
        self.bc = bc
        self.config = config

        # canonical activity label lookup
        self._activity_label_map = {
            self._normalize_symbol(a): a
            for a in self.bc.get_business_context_activities()
        }
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def find_plan(self, init_state: List[str], final_state: List[str]) -> Optional[ProcessStructureTree]:
        work_dir = Path(self.config.work_dir).resolve()
        work_dir.mkdir(parents=True, exist_ok=True)

        domain_path = work_dir / "domain.pddl"
        problem_path = work_dir / "problem.pddl"

        domain_path.write_text(self._prepare_domain_pddl(), encoding="utf-8")
        problem_path.write_text(self._prepare_problem_pddl(init_state, final_state), encoding="utf-8")

        ok = self._run_fast_downward(domain_path, problem_path, work_dir)
        if not ok:
            return None

        plan_path = self._pick_plan_file(work_dir)
        if plan_path is None or not plan_path.exists():
            return None

        plan_lines = self._read_plan_file(plan_path)
        if not plan_lines:
            return None

        # Build PST from plan
        pst = self._construct_tree_from_plan(plan_lines)

        # Optional: write debug artifacts so you can inspect what FD produced
        if self.config.keep_output:
            (work_dir / "fd_plan_lines.txt").write_text("\n".join(plan_lines) + "\n", encoding="utf-8")
            (work_dir / "fd_plan_pst.txt").write_text(str(pst) + "\n", encoding="utf-8")

        return pst

    # ------------------------------------------------------------------
    # Fast Downward execution
    # ------------------------------------------------------------------
    def _run_fast_downward(self, domain: Path, problem: Path, work_dir: Path) -> bool:
        fd_script = Path(self.config.fd_path).resolve()
        if fd_script.is_dir():
            fd_script = fd_script / "fast-downward.py"
        if not fd_script.exists():
            raise FileNotFoundError(f"Fast Downward not found at: {fd_script}")

        # remove old plan files: sas_plan, sas_plan.1, ...
        for p in work_dir.glob(f"{self.config.plan_file}*"):
            try:
                p.unlink()
            except Exception:
                pass

        cmd = [
            self.config.python_exe,
            str(fd_script),
            "--alias",
            self.config.alias,
            "--plan-file",
            self.config.plan_file,
            str(domain),
            str(problem),
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.config.timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired:
            (work_dir / "fd_timeout.txt").write_text(
                f"Timed out after {self.config.timeout_sec}s\nCMD: {' '.join(cmd)}\n",
                encoding="utf-8",
            )
            return False

        if self.config.keep_output:
            (work_dir / "fd_stdout.txt").write_text(proc.stdout or "", encoding="utf-8")

        # success if any plan file exists (sas_plan or sas_plan.N)
        return self._pick_plan_file(work_dir) is not None

    def _pick_plan_file(self, work_dir: Path) -> Optional[Path]:
        exact = work_dir / self.config.plan_file
        if exact.exists():
            return exact
        candidates = sorted(work_dir.glob(f"{self.config.plan_file}.*"))
        return candidates[-1] if candidates else None

    # ------------------------------------------------------------------
    # Plan parsing
    # ------------------------------------------------------------------
    def _read_plan_file(self, plan_path: Path) -> List[str]:
        lines: List[str] = []
        for raw in plan_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = raw.strip()
            if not s or s.startswith(";"):
                continue
            lines.append(s)
        return lines

    def _construct_tree_from_plan(self, plan_lines: List[str]) -> ProcessStructureTree:
        """
        sas_plan lines usually look like:
            (execute_receive_application1 risk certificate)
        We parse the action name and convert into a Sequence of Activity nodes.
        """
        root = Node(node_type=NodeType.Sequence)
        root.condition = "true"
        pst = ProcessStructureTree.from_root(root)

        for line in plan_lines:
            action = self._extract_action_name(line)
            if not action:
                continue

            act_label = self._canonical_activity_label(
                self._restore_activity_name_from_action(action)
            )

            nd = Node(node_type=NodeType.Activity)
            nd.set_label(act_label)
            pst.insert_node(nd, root, pos=len(root.get_children()) + 1)

        return pst

    @staticmethod
    def _extract_action_name(plan_line: str) -> Optional[str]:
        s = plan_line.strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()
        if not s:
            return None
        return s.split()[0]

    #@staticmethod
    def _restore_activity_name_from_action(self, action_name: str) -> str:
        """
        Convert Fast Downward action name like:
          execute_receive_application1
        back to the canonical BusinessContext activity label, e.g.
          "Receive Application"
        """
        a = (action_name or "").strip().lower()

        # strip execute_ prefix
        if a.startswith("execute_"):
            a = a[len("execute_"):]

        # strip trailing counter digits
        a = re.sub(r"\d+$", "", a)

        # action names use underscores; normalize to canonical key (hyphen-based)
        a = a.replace("_", "-")

        key = self._normalize_symbol(a)

        # return canonical label if known
        if key in self._activity_label_map:
            return self._activity_label_map[key]

        # fallback: best-effort pretty label
        pretty = a.replace("-", " ").strip()
        return pretty.title()

    # ------------------------------------------------------------------
    # PDDL generation (updated: executed-* as 0-arity predicates)
    # ------------------------------------------------------------------
    def _prepare_domain_pddl(self) -> str:
        """
        Domain with one predicate per data-state, plus one 0-arity executed predicate per activity.
        This avoids representing activities as objects (which caused the 'Undefined object' error).
        """
        domain = "(define (domain business-context)\n"
        domain += "(:requirements :strips)\n"
        domain += "(:predicates\n"

        # executed predicates: one per activity, 0-arity
        for act in self.bc.get_business_context_activities():
            domain += f"  ({self._executed_pred_name(act)})\n"

        # one predicate per data-state
        seen = set()
        for s in self.bc.get_all_data_object_states():
            pred = s.lower().strip()
            if not pred:
                continue
            if pred not in seen:
                seen.add(pred)
                domain += f"  ({pred} ?obj)\n"

        domain += ")\n"
        domain += "; ACTIONS\n"

        for act in self.bc.get_business_context_activities():
            cnt = 1

            pre_cond = self.bc.get_activity_data_precondition(act) or ""
            post_p = self.bc.get_activity_data_postcondition_positive(act) or ""
            post_n = self.bc.get_activity_data_postcondition_negative(act) or ""

            pre_cond_a = [x.strip() for x in pre_cond.split(",")] if pre_cond.strip() else [""]
            post_pa = [x.strip() for x in post_p.split(",")] if post_p.strip() else [""]
            post_na = [x.strip() for x in post_n.split(",")] if post_n.strip() else [""]

            for pre_i in pre_cond_a:
                for post_nj in post_na:
                    for post_pk in post_pa:
                        parameters = self._build_parameters(pre_i, post_nj, post_pk)
                        pre_pddl = self._generate_conjunctive_pre(pre_i)
                        eff_pddl = self._generate_conjunctive_post(post_pk, post_nj, act)

                        action_name = f"execute_{act.replace(' ', '_')}{cnt}".lower()
                        domain += f"(:action {action_name}\n"
                        domain += f"  {parameters}\n"
                        domain += f"  :precondition {pre_pddl}\n"
                        domain += f"  :effect {eff_pddl}\n"
                        domain += ")\n"
                        cnt += 1

        domain += ")\n"
        return domain

    def _prepare_problem_pddl(self, initial_state: List[str], target_state: List[str]) -> str:
        problem = "(define (problem planning-problem)\n"
        problem += "(:domain business-context)\n"

        # objects: ONLY data objects (risk, certificate, etc.). No activity objects.
        problem += "(:objects\n"
        added: List[str] = []
        for s in self.bc.get_all_data_object_states():
            dob = self._get_data_object_name(s).lower().strip()
            if dob and dob not in added:
                problem += f"  {dob}\n"
                added.append(dob)
        problem += ")\n"

        # init
        problem += "(:init\n"
        for i in initial_state:
            i = (i or "").strip()
            if not i:
                continue

            ex = self._maybe_executed_atom(i)
            if ex is not None:
                # executed predicates are 0-arity: (executed-xyz)
                problem += f"  {ex}\n"
                continue

            # regular data state: (state obj)
            state = i.lower()
            obj = self._get_data_object_name(i).lower().strip()
            problem += f"  ({state} {obj})\n"
        problem += ")\n"

        # goal
        problem += "(:goal (and\n"
        for i in target_state:
            i = (i or "").strip()
            if not i:
                continue

            ex = self._maybe_executed_atom(i, allow_negation=True)
            if ex is not None:
                problem += f"  {ex}\n"
                continue

            # regular data state goal
            state = i.lower()
            obj = self._get_data_object_name(i).lower().strip()
            problem += f"  ({state} {obj})\n"

        problem += "))\n"
        problem += ")\n"
        return problem

    def _build_parameters(self, pre: str, post_n: str, post_p: str) -> str:
        added: List[str] = []
        params = ":parameters("

        for c in self._separate_data_states(pre):
            dob = self._get_data_object_name(c).lower()
            if dob and dob not in added:
                params += f"?{dob} "
                added.append(dob)

        for c in self._separate_data_states(post_n):
            dob = self._get_data_object_name(c).lower()
            if dob and dob not in added:
                params += f"?{dob} "
                added.append(dob)

        for c in self._separate_data_states(post_p):
            dob = self._get_data_object_name(c).lower()
            if dob and dob not in added:
                params += f"?{dob} "
                added.append(dob)

        params += ")"
        return params

    @staticmethod
    def _separate_data_states(s: str) -> List[str]:
        if not s or not s.strip():
            return []
        return [c.strip() for c in s.split("and") if c.strip()]

    def _generate_conjunctive_pre(self, s: str) -> str:
        s = (s or "").strip()
        if not s:
            return "(and)"  # empty conjunction

        result = "(and "
        for ss in self._separate_data_states(s):
            result += f"({ss.lower()} ?{self._get_data_object_name(ss).lower()}) "
        result += ")"
        return result

    def _generate_conjunctive_post(self, s_pos: str, s_neg: str, actname: str) -> str:
        # executed predicate is 0-arity
        result = f"(and ({self._executed_pred_name(actname)}) "

        for ss in self._separate_data_states(s_pos):
            result += f"({ss.lower()} ?{self._get_data_object_name(ss).lower()}) "

        for ss in self._separate_data_states(s_neg):
            result += f"(not ({ss.lower()} ?{self._get_data_object_name(ss).lower()})) "

        result += ")"
        return result

    # ------------------------------------------------------------------
    # Executed predicate helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_symbol(s: str) -> str:
        """
        Turn labels like 'issue certificate' or 'issue-certificate' into a PDDL-safe token.
        """
        s = (s or "").strip().lower()
        s = s.replace("_", "-").replace(" ", "-")
        s = re.sub(r"[^a-z0-9\-]", "", s)
        s = re.sub(r"-+", "-", s).strip("-")
        return s

    def _executed_pred_name(self, activity_name: str) -> str:
        """
        Returns executed predicate name for an activity, e.g. 'executed-issue-certificate'
        """
        return f"executed-{self._normalize_symbol(activity_name)}"

    def _maybe_executed_atom(self, raw: str, allow_negation: bool = False) -> Optional[str]:
        """
        Accepts and converts executed markers into full PDDL atoms:

          - 'executed issue certificate'  -> '(executed-issue-certificate)'
          - 'executed-issue-certificate'  -> '(executed-issue-certificate)'
          - '!executed issue certificate' -> '(not (executed-issue-certificate))'  (if allow_negation=True)
          - '!executed-issue-certificate' -> '(not (executed-issue-certificate))'  (if allow_negation=True)

        Returns None if the string isn't an executed marker.
        """
        s = (raw or "").strip()

        neg = False
        if s.startswith("!"):
            neg = True
            s = s[1:].strip()
            if not allow_negation:
                return None

        s_low = s.lower()

        # Case 1: already executed-*
        if s_low.startswith("executed-"):
            pred = self._normalize_symbol(s_low)  # keeps executed- prefix
            atom = f"({pred})"
            return f"(not {atom})" if neg else atom

        # Case 2: "executed <activity...>"
        if s_low.startswith("executed"):
            rest = s_low[len("executed"):].strip()
            if not rest:
                return None
            pred = self._executed_pred_name(rest)
            atom = f"({pred})"
            return f"(not {atom})" if neg else atom

        return None

    # ------------------------------------------------------------------
    # Data-object name extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _get_data_object_name(state_expr: str) -> str:
        s = (state_expr or "").strip()
        if "_" not in s:
            return s
        return s.rsplit("_", 1)[0]

    def _canonical_activity_label(self, label: str) -> str:
        key = self._normalize_symbol(label)
        return self._activity_label_map.get(key, label.title())
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class BusinessContext:
    """
    Business context used by planner + resolver.

    Supports:
    - default loading (legacy)
    - scenario-based loading via load_from_defaults_module()

    IMPORTANT:
    - Tracks BOTH:
        (a) split dob_states (legacy)
        (b) full predicate tokens (state_tokens) to avoid missing predicates like case_assigned
    """

    # legacy split representation: dob -> "state1,state2"
    dob_states: Dict[str, str] = field(default_factory=dict)

    # NEW: robust representation: full tokens like {"case_unassigned", "case_assigned"}
    state_tokens: Set[str] = field(default_factory=set)

    contra_states: Dict[str, str] = field(default_factory=dict)
    activities: List[str] = field(default_factory=list)

    activities_preconditions: Dict[str, str] = field(default_factory=dict)
    activities_postconditions_positive: Dict[str, str] = field(default_factory=dict)
    activities_postconditions_negative: Dict[str, str] = field(default_factory=dict)

    contra_activities: Dict[str, str] = field(default_factory=dict)

    model_uri: Optional[str] = None

    # Scenario initial state support (optional; backward-compatible)
    initial_state: str = "risk_initial and certificate_initial"
    initial_state_alternatives: List[str] = field(default_factory=list)

    # -------------------------------------------------
    # Loading
    # -------------------------------------------------
    def full_load(self, mode: str = "DEFAULT") -> None:
        """
        Prevent re-loading if scenario defaults already populated BC.
        """
        if self.activities:
            return

        if mode.upper() == "DATABASE":
            self.load_contradicting_activities()
            self.load_contradicting_states()
            self.load_data_postconditions_of_activities()
            self.load_data_preconditions_of_activities()
        else:
            self.load_defaults()

    def load_defaults(self) -> None:
        from src.context.defaults import (
            DEFAULT_CONTRADICTING_STATES,
            DEFAULT_CONTRADICTING_ACTIVITIES,
            DEFAULT_ACTIVITIES,
            DEFAULT_ACTIVITY_PRECONDITIONS,
            DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE,
            DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE,
        )

        self.load_from_defaults_module(
            type(
                "DefaultsModule",
                (),
                dict(
                    DEFAULT_CONTRADICTING_STATES=DEFAULT_CONTRADICTING_STATES,
                    DEFAULT_CONTRADICTING_ACTIVITIES=DEFAULT_CONTRADICTING_ACTIVITIES,
                    DEFAULT_ACTIVITIES=DEFAULT_ACTIVITIES,
                    DEFAULT_ACTIVITY_PRECONDITIONS=DEFAULT_ACTIVITY_PRECONDITIONS,
                    DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE=DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE,
                    DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE=DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE,
                ),
            )
        )

    # -------------------------------------------------
    # Scenario loading
    # -------------------------------------------------
    def load_from_defaults_module(self, module) -> None:
        """
        Load a scenario defaults module (e.g., src.context.some_scenario_defaults).

        Supports optional:
          - DEFAULT_INITIAL_STATE (string, "a and b and c")
          - DEFAULT_INITIAL_STATE_ALTERNATIVES (list of strings)

        Backward-compatible: if not provided, resolver will fall back to "*_initial" heuristic.
        """

        # reset
        self.activities.clear()
        self.activities_preconditions.clear()
        self.activities_postconditions_positive.clear()
        self.activities_postconditions_negative.clear()
        self.contra_states.clear()
        self.contra_activities.clear()
        self.dob_states.clear()
        self.state_tokens.clear()

        # scenario initial states (optional)
        self.initial_state = getattr(module, "DEFAULT_INITIAL_STATE", "") or ""
        self.initial_state_alternatives = list(getattr(module, "DEFAULT_INITIAL_STATE_ALTERNATIVES", []) or [])

        # contradictions
        self.contra_states.update(getattr(module, "DEFAULT_CONTRADICTING_STATES", {}) or {})
        self.contra_activities.update(getattr(module, "DEFAULT_CONTRADICTING_ACTIVITIES", {}) or {})

        # activities + pre/post
        acts = getattr(module, "DEFAULT_ACTIVITIES", []) or []
        pre = getattr(module, "DEFAULT_ACTIVITY_PRECONDITIONS", {}) or {}
        pos = getattr(module, "DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE", {}) or {}
        neg = getattr(module, "DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE", {}) or {}

        for act in acts:
            key = act.lower().strip()
            self.add_activity(
                act,
                pre=pre.get(key),
                post_pos=pos.get(key),
                post_neg=neg.get(key),
            )

        # ensure all states are registered
        for expr in list(pre.values()) + list(pos.values()) + list(neg.values()):
            if expr:
                self.insert_data_object_state(expr)

        # ALSO register tokens from initial states, because they appear in :init
        for init_list in self.get_initial_state_alternatives():
            for tok in init_list:
                self._register_state_token(tok)

    def get_initial_state_alternatives(self) -> List[List[str]]:
        """
        Returns a list of initial fact lists.

        Preferred:
          - DEFAULT_INITIAL_STATE_ALTERNATIVES (each "a and b")
          - else DEFAULT_INITIAL_STATE

        Fallback (legacy behavior):
          - include all data-object-states whose token contains "initial"
        """

        def parse(expr: str) -> List[str]:
            out: List[str] = []
            for part in expr.split("and"):
                t = part.strip()
                if t:
                    out.append(t)
            return out

        if self.initial_state_alternatives:
            return [parse(e) for e in self.initial_state_alternatives if e and e.strip()]

        if self.initial_state and self.initial_state.strip():
            return [parse(self.initial_state)]

        # legacy fallback: any state token containing "initial"
        legacy: List[str] = []
        for s in self.get_all_data_object_states():
            if "initial" in s:
                legacy.append(s)
        return [legacy] if legacy else [[]]

    # -------------------------------------------------
    # DB hooks (unused)
    # -------------------------------------------------
    def load_contradicting_states(self) -> None:
        raise NotImplementedError()

    def load_contradicting_activities(self) -> None:
        raise NotImplementedError()

    def load_data_preconditions_of_activities(self) -> None:
        raise NotImplementedError()

    def load_data_postconditions_of_activities(self) -> None:
        raise NotImplementedError()

    # -------------------------------------------------
    # Data-object helpers
    # -------------------------------------------------
    def _register_state_token(self, token: str) -> None:
        """
        Register a state token robustly.
        Keeps both:
          - full token (state_tokens)
          - legacy split form (dob_states)
        """
        tok = token.strip()
        if not tok:
            return
        if tok.upper().startswith("EXECUTED"):
            return
        if tok.upper().startswith("!EXECUTED"):
            return

        # full token is what your PDDL generator uses as predicate name
        self.state_tokens.add(tok)

        # legacy split storage (kept for compatibility)
        dob = self._get_data_object_name(tok)
        st = self._get_data_object_state(tok)

        if dob in self.dob_states:
            existing = [x.strip() for x in self.dob_states[dob].split(",") if x.strip()]
            if st not in existing:
                self.dob_states[dob] = self.dob_states[dob] + "," + st
        else:
            self.dob_states[dob] = st

    def insert_data_object_state(self, expr: str) -> None:
        if not expr:
            return

        disj = [p.strip() for p in expr.split(",") if p.strip()]
        for part in disj:
            conj = [p.strip() for p in part.split("and") if p.strip()]
            for token in conj:
                self._register_state_token(token)

    @staticmethod
    def _get_data_object_name(state_expr: str) -> str:
        return state_expr.rsplit("_", 1)[0] if "_" in state_expr else state_expr

    @staticmethod
    def _get_data_object_state(state_expr: str) -> str:
        return state_expr.rsplit("_", 1)[1] if "_" in state_expr else state_expr

    # -------------------------------------------------
    # Query API
    # -------------------------------------------------
    def get_contradicting_state(self, state: str) -> Optional[str]:
        return self.contra_states.get(state)

    def get_contradicting_activities(self, act: str) -> Optional[str]:
        return self.contra_activities.get(act.lower())

    def get_activity_data_postcondition_positive(self, actname: str) -> Optional[str]:
        return self.activities_postconditions_positive.get(actname.lower())

    def get_activity_data_postcondition_negative(self, actname: str) -> Optional[str]:
        return self.activities_postconditions_negative.get(actname.lower())

    def get_activity_data_precondition(self, actname: str) -> Optional[str]:
        return self.activities_preconditions.get(actname.lower())

    def get_business_context_activities(self) -> List[str]:
        return list(self.activities)

    def has_activity(self, actname: str) -> bool:
        return actname.lower().strip() in set(self.activities)

    def get_all_data_object_states(self) -> List[str]:
        """
        IMPORTANT:
        Return full predicate tokens so your PDDL (:predicates) contains
        everything that appears in preconditions/effects/init.

        This fixes missing predicate declarations like (case_assigned ?obj).
        """
        return sorted(self.state_tokens)

    # -------------------------------------------------
    # Activity insertion
    # -------------------------------------------------
    def add_activity(
        self,
        name: str,
        pre: Optional[str] = None,
        post_pos: Optional[str] = None,
        post_neg: Optional[str] = None,
    ) -> None:
        key = name.lower().strip()

        if key not in self.activities:
            self.activities.append(key)

        if pre is not None:
            self.activities_preconditions[key] = pre
            self.insert_data_object_state(pre)

        if post_pos is not None:
            self.activities_postconditions_positive[key] = post_pos
            self.insert_data_object_state(post_pos)

        if post_neg is not None:
            self.activities_postconditions_negative[key] = post_neg
            self.insert_data_object_state(post_neg)

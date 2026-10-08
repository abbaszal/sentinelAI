import json
import re

from dataclasses import dataclass, field
from typing import Any, Protocol


# ---------------------------------------------------------
# Trace protocol
# ---------------------------------------------------------

class ToolTraceLike(Protocol):
    """
    Minimal interface required from an agent tool trace.
    """

    tool_name: str
    arguments: dict[str, Any]
    is_error: bool
    result: Any | None


# ---------------------------------------------------------
# Verification models
# ---------------------------------------------------------

@dataclass
class VerificationIssue:
    """
    One reason a proposed answer cannot yet be accepted.
    """

    code: str
    message: str


@dataclass
class VerificationAction:
    """
    Mandatory MCP action required to obtain evidence.
    """

    tool_name: str
    arguments: dict[str, Any]
    reason: str


@dataclass
class VerificationResult:
    """
    Complete result from the EvidenceGate.
    """

    passed: bool

    issues: list[
        VerificationIssue
    ] = field(
        default_factory=list
    )

    required_actions: list[
        VerificationAction
    ] = field(
        default_factory=list
    )

    @property
    def feedback(
        self,
    ) -> str:
        """
        Message that can be returned to the LLM when
        verification fails.
        """

        if self.passed:
            return "Verification passed."

        lines = [
            "VERIFICATION GATE REJECTED THE PROPOSED FINAL ANSWER.",
            "",
            "Do not give the final answer yet.",
            "",
            "Verification problems:",
        ]

        for issue in self.issues:

            lines.append(
                f"- {issue.message}"
            )

        if self.required_actions:

            lines.extend(
                [
                    "",
                    "Mandatory evidence actions:",
                ]
            )

            for action in (
                self.required_actions
            ):

                lines.append(
                    "- "
                    f"{action.tool_name}"
                    f"({action.arguments})"
                )

        lines.extend(
            [
                "",
                (
                    "Use only verified operational "
                    "and policy evidence."
                ),
                (
                    "Include every verified affected "
                    "order and its verified amount."
                ),
                (
                    "Do not invent NovaShop rules or "
                    "operational facts."
                ),
            ]
        )

        return "\n".join(
            lines
        )


# ---------------------------------------------------------
# Evidence Gate
# ---------------------------------------------------------

class EvidenceGate:
    """
    Deterministic verification component.

    Responsibilities:

    1. Determine mandatory evidence.
    2. Recommend still-missing tool calls.
    3. Detect contradictions.
    4. Detect missing verified facts in final answers.

    Intent detection remains keyword based for now.
    """

    DUPLICATE_PATTERNS = (
        "charged twice",
        "charged two times",
        "double charged",
        "double-charged",
        "duplicate payment",
        "duplicate charge",
        "paid twice",
    )

    POLICY_REQUEST_PATTERNS = (
        "policy",
        "what should happen",
        "should happen next",
        "what happens next",
        "according to novashop",
        "what does novashop say",
    )

    POSITIVE_DUPLICATE_CONTRADICTIONS = (
        "no duplicate payment",
        "no duplicate payments",
        "no duplicate charge",
        "no duplicate charges",
        "duplicate payment was not detected",
        "duplicate payments were not detected",
        "no duplicate payments were detected",
        "no duplicate payment was detected",
        "appears to be a misunderstanding",
        "appears to be a false report",
        "false report",
    )

    NEGATIVE_DUPLICATE_CONTRADICTIONS = (
        "duplicate payment was confirmed",
        "duplicate payments were confirmed",
        "duplicate payment was detected",
        "duplicate payments were detected",
    )

    # -----------------------------------------------------
    # Main verification
    # -----------------------------------------------------

    def verify(
        self,
        user_request: str,
        tool_traces: list[
            ToolTraceLike
        ],
        proposed_answer: str,
    ) -> VerificationResult:

        issues: list[
            VerificationIssue
        ] = []

        actions: list[
            VerificationAction
        ] = []

        request_lower = (
            user_request.lower()
        )

        answer_lower = (
            proposed_answer.lower()
        )

        duplicate_intent = (
            self._contains_any(
                request_lower,
                self.DUPLICATE_PATTERNS,
            )
        )

        policy_required = (
            self._contains_any(
                request_lower,
                self.POLICY_REQUEST_PATTERNS,
            )
            or self._answer_makes_policy_claim(
                answer_lower
            )
        )

        # ---------------------------------------------
        # Required duplicate-payment evidence
        # ---------------------------------------------

        if duplicate_intent:

            (
                duplicate_issues,
                duplicate_actions,
            ) = self._verify_duplicate_evidence(
                user_request=user_request,
                tool_traces=tool_traces,
            )

            issues.extend(
                duplicate_issues
            )

            actions.extend(
                duplicate_actions
            )

        # ---------------------------------------------
        # Required policy evidence
        # ---------------------------------------------

        if policy_required:

            policy_query = (
                self._build_policy_query(
                    user_request=(
                        user_request
                    ),
                    duplicate_intent=(
                        duplicate_intent
                    ),
                )
            )

            (
                policy_issues,
                policy_actions,
            ) = self._verify_policy_evidence(
                tool_traces=tool_traces,
                policy_query=policy_query,
            )

            issues.extend(
                policy_issues
            )

            actions.extend(
                policy_actions
            )

        # ---------------------------------------------
        # Only evaluate answer content when there is
        # actually a proposed final answer.
        #
        # recommend_next_actions() calls verify("")
        # internally, so we intentionally skip answer
        # checks in that case.
        # ---------------------------------------------

        if proposed_answer.strip():

            issues.extend(
                self._verify_answer_consistency(
                    tool_traces=(
                        tool_traces
                    ),
                    proposed_answer=(
                        proposed_answer
                    ),
                )
            )

            issues.extend(
                self._verify_answer_completeness(
                    tool_traces=(
                        tool_traces
                    ),
                    proposed_answer=(
                        proposed_answer
                    ),
                )
            )

        # ---------------------------------------------
        # Remove duplicates
        # ---------------------------------------------

        issues = (
            self._deduplicate_issues(
                issues
            )
        )

        actions = (
            self._deduplicate_actions(
                actions
            )
        )

        return VerificationResult(
            passed=(
                len(issues) == 0
            ),
            issues=issues,
            required_actions=actions,
        )

    # -----------------------------------------------------
    # Proactive guidance
    # -----------------------------------------------------

    def recommend_next_actions(
        self,
        user_request: str,
        tool_traces: list[
            ToolTraceLike
        ],
    ) -> list[
        VerificationAction
    ]:
        """
        Return mandatory evidence actions that have not
        successfully happened yet.
        """

        verification = self.verify(
            user_request=user_request,
            tool_traces=tool_traces,
            proposed_answer="",
        )

        return (
            verification.required_actions
        )

    def build_next_action_guidance(
        self,
        user_request: str,
        tool_traces: list[
            ToolTraceLike
        ],
    ) -> str | None:
        """
        Short planning guidance for the LLM.

        Advisory only. The controller does not execute
        these recommendations at this stage.
        """

        actions = (
            self.recommend_next_actions(
                user_request=(
                    user_request
                ),
                tool_traces=(
                    tool_traces
                ),
            )
        )

        if not actions:
            return None

        lines = [
            "VERIFIER GUIDANCE:",
            (
                "The investigation is not yet supported "
                "by all required evidence."
            ),
            "",
            "Still-required evidence actions:",
        ]

        for action in actions:

            lines.append(
                f"- {action.tool_name}"
                f"({action.arguments})"
            )

        lines.extend(
            [
                "",
                (
                    "Prefer these missing evidence "
                    "actions before unrelated tools."
                ),
                (
                    "Do not repeat a tool call that "
                    "already succeeded."
                ),
                (
                    "You may use another tool only if "
                    "it is genuinely useful."
                ),
            ]
        )

        return "\n".join(
            lines
        )

    # -----------------------------------------------------
    # Duplicate-payment evidence requirements
    # -----------------------------------------------------

    def _verify_duplicate_evidence(
        self,
        user_request: str,
        tool_traces: list[
            ToolTraceLike
        ],
    ) -> tuple[
        list[VerificationIssue],
        list[VerificationAction],
    ]:

        issues: list[
            VerificationIssue
        ] = []

        actions: list[
            VerificationAction
        ] = []

        customer_id = (
            self._extract_customer_id(
                user_request
            )
        )

        explicit_order_ids = (
            self._extract_order_ids(
                user_request
            )
        )

        target_order_ids = set(
            explicit_order_ids
        )

        # ---------------------------------------------
        # Customer is known but orders are not.
        # ---------------------------------------------

        if (
            not target_order_ids
            and customer_id is not None
        ):

            get_orders_trace = (
                self._find_successful_trace(
                    tool_traces=(
                        tool_traces
                    ),
                    tool_name=(
                        "get_orders"
                    ),
                    argument_name=(
                        "customer_id"
                    ),
                    argument_value=(
                        customer_id
                    ),
                )
            )

            if get_orders_trace is None:

                issues.append(
                    VerificationIssue(
                        code=(
                            "missing_customer_orders"
                        ),
                        message=(
                            f"Customer {customer_id} "
                            "is known, but their orders "
                            "have not been retrieved."
                        ),
                    )
                )

                actions.append(
                    VerificationAction(
                        tool_name=(
                            "get_orders"
                        ),
                        arguments={
                            "customer_id": (
                                customer_id
                            )
                        },
                        reason=(
                            "Relevant order IDs must be "
                            "discovered before duplicate "
                            "payment checks."
                        ),
                    )
                )

                return (
                    issues,
                    actions,
                )

            target_order_ids.update(
                self._order_ids_from_result(
                    get_orders_trace.result
                )
            )

        # ---------------------------------------------
        # No identifiers available.
        # ---------------------------------------------

        if (
            not target_order_ids
            and customer_id is None
        ):

            return (
                issues,
                actions,
            )

        # ---------------------------------------------
        # Determine which orders already have a trusted
        # duplicate-payment result.
        # ---------------------------------------------

        checked_order_ids: set[
            int
        ] = set()

        for trace in tool_traces:

            if trace.is_error:
                continue

            if (
                trace.tool_name
                != "detect_duplicate_payment"
            ):
                continue

            order_id = (
                trace.arguments.get(
                    "order_id"
                )
            )

            if isinstance(
                order_id,
                int,
            ):

                checked_order_ids.add(
                    order_id
                )

        missing_order_ids = (
            target_order_ids
            - checked_order_ids
        )

        if missing_order_ids:

            missing_display = ", ".join(
                str(order_id)
                for order_id
                in sorted(
                    missing_order_ids
                )
            )

            issues.append(
                VerificationIssue(
                    code=(
                        "missing_duplicate_checks"
                    ),
                    message=(
                        "Duplicate-payment status must "
                        "use the trusted deterministic "
                        "rule for these relevant orders: "
                        f"{missing_display}."
                    ),
                )
            )

            for order_id in sorted(
                missing_order_ids
            ):

                actions.append(
                    VerificationAction(
                        tool_name=(
                            "detect_duplicate_payment"
                        ),
                        arguments={
                            "order_id": (
                                order_id
                            )
                        },
                        reason=(
                            "Trusted deterministic "
                            "duplicate-payment evidence "
                            "is required."
                        ),
                    )
                )

        return (
            issues,
            actions,
        )

    # -----------------------------------------------------
    # Policy evidence
    # -----------------------------------------------------

    def _verify_policy_evidence(
        self,
        tool_traces: list[
            ToolTraceLike
        ],
        policy_query: str,
    ) -> tuple[
        list[VerificationIssue],
        list[VerificationAction],
    ]:

        for trace in tool_traces:

            if trace.is_error:
                continue

            if (
                trace.tool_name
                != "search_policy"
            ):
                continue

            result = trace.result

            if not isinstance(
                result,
                dict,
            ):
                continue

            results = (
                result.get(
                    "results"
                )
            )

            if (
                isinstance(
                    results,
                    list,
                )
                and len(results) > 0
            ):

                return (
                    [],
                    [],
                )

        return (
            [
                VerificationIssue(
                    code=(
                        "missing_policy_evidence"
                    ),
                    message=(
                        "The answer depends on "
                        "NovaShop policy, but no "
                        "retrieved policy evidence "
                        "exists."
                    ),
                )
            ],
            [
                VerificationAction(
                    tool_name=(
                        "search_policy"
                    ),
                    arguments={
                        "query": (
                            policy_query
                        ),
                        "top_k": 3,
                    },
                    reason=(
                        "Policy claims must be "
                        "grounded in retrieved "
                        "NovaShop policy evidence."
                    ),
                )
            ],
        )

    # -----------------------------------------------------
    # Contradiction verification
    # -----------------------------------------------------

    def _verify_answer_consistency(
        self,
        tool_traces: list[
            ToolTraceLike
        ],
        proposed_answer: str,
    ) -> list[
        VerificationIssue
    ]:

        answer_lower = (
            proposed_answer.lower()
        )

        duplicate_results: list[
            bool
        ] = []

        for trace in tool_traces:

            if trace.is_error:
                continue

            if (
                trace.tool_name
                != "detect_duplicate_payment"
            ):
                continue

            if not isinstance(
                trace.result,
                dict,
            ):
                continue

            duplicate = (
                trace.result.get(
                    "duplicate_payment"
                )
            )

            if isinstance(
                duplicate,
                bool,
            ):

                duplicate_results.append(
                    duplicate
                )

        if not duplicate_results:
            return []

        issues: list[
            VerificationIssue
        ] = []

        # ---------------------------------------------
        # At least one trusted result says TRUE.
        # ---------------------------------------------

        if any(
            duplicate_results
        ):

            if self._contains_any(
                answer_lower,
                self.POSITIVE_DUPLICATE_CONTRADICTIONS,
            ):

                issues.append(
                    VerificationIssue(
                        code=(
                            "duplicate_contradiction"
                        ),
                        message=(
                            "The proposed answer denies "
                            "a duplicate payment, but "
                            "trusted deterministic "
                            "evidence confirms at least "
                            "one duplicate."
                        ),
                    )
                )

        # ---------------------------------------------
        # Every trusted result says FALSE.
        # ---------------------------------------------

        elif all(
            duplicate is False
            for duplicate
            in duplicate_results
        ):

            if self._contains_any(
                answer_lower,
                self.NEGATIVE_DUPLICATE_CONTRADICTIONS,
            ):

                issues.append(
                    VerificationIssue(
                        code=(
                            "duplicate_contradiction"
                        ),
                        message=(
                            "The proposed answer claims "
                            "a duplicate was confirmed, "
                            "but every trusted duplicate "
                            "check returned false."
                        ),
                    )
                )

        return issues

    # -----------------------------------------------------
    # NEW:
    # Final-answer completeness verification
    # -----------------------------------------------------

    def _verify_answer_completeness(
        self,
        tool_traces: list[
            ToolTraceLike
        ],
        proposed_answer: str,
    ) -> list[
        VerificationIssue
    ]:
        """
        Every confirmed duplicate-payment result must be
        represented in the final answer.

        For each:

            duplicate_payment = True

        the answer must contain:

            Order <ID>
            overpayment amount

        Example:

            Order 2
            $49.99

        This prevents the model from correctly collecting
        evidence for Orders 2 and 3 but mentioning only
        Order 3 in its final answer.
        """

        issues: list[
            VerificationIssue
        ] = []

        confirmed_duplicates = (
            self._confirmed_duplicate_facts(
                tool_traces
            )
        )

        for (
            order_id,
            overpayment_amount,
        ) in confirmed_duplicates:

            mentions_order = (
                self._answer_mentions_order(
                    answer=(
                        proposed_answer
                    ),
                    order_id=(
                        order_id
                    ),
                )
            )

            mentions_amount = (
                self._answer_mentions_amount(
                    answer=(
                        proposed_answer
                    ),
                    amount=(
                        overpayment_amount
                    ),
                )
            )

            # -----------------------------------------
            # Neither order nor amount is present.
            # -----------------------------------------

            if (
                not mentions_order
                and not mentions_amount
            ):

                issues.append(
                    VerificationIssue(
                        code=(
                            "missing_duplicate_order_fact"
                        ),
                        message=(
                            "The final answer omits "
                            "verified facts for "
                            f"Order {order_id}. "
                            "Explicitly mention "
                            f"Order {order_id} and its "
                            "verified overpayment amount "
                            f"{overpayment_amount:.2f}."
                        ),
                    )
                )

                continue

            # -----------------------------------------
            # Amount exists, but order is missing.
            # -----------------------------------------

            if not mentions_order:

                issues.append(
                    VerificationIssue(
                        code=(
                            "missing_duplicate_order_fact"
                        ),
                        message=(
                            "The final answer does not "
                            "explicitly identify "
                            f"Order {order_id}, even "
                            "though a duplicate payment "
                            "was confirmed for that order."
                        ),
                    )
                )

            # -----------------------------------------
            # Order exists, amount is missing.
            # -----------------------------------------

            if not mentions_amount:

                issues.append(
                    VerificationIssue(
                        code=(
                            "missing_overpayment_fact"
                        ),
                        message=(
                            f"The final answer mentions "
                            f"Order {order_id} but omits "
                            "its verified overpayment "
                            f"amount of "
                            f"{overpayment_amount:.2f}."
                        ),
                    )
                )

        return issues

    # -----------------------------------------------------
    # Extract confirmed duplicate facts
    # -----------------------------------------------------

    @staticmethod
    def _confirmed_duplicate_facts(
        tool_traces: list[
            ToolTraceLike
        ],
    ) -> list[
        tuple[int, float]
    ]:
        """
        Extract:

            (order_id, overpayment_amount)

        only from successful trusted duplicate-payment
        results where duplicate_payment == True.
        """

        facts: dict[
            int,
            float,
        ] = {}

        for trace in tool_traces:

            if trace.is_error:
                continue

            if (
                trace.tool_name
                != "detect_duplicate_payment"
            ):
                continue

            if not isinstance(
                trace.result,
                dict,
            ):
                continue

            order_id = (
                trace.result.get(
                    "order_id"
                )
            )

            duplicate = (
                trace.result.get(
                    "duplicate_payment"
                )
            )

            overpayment = (
                trace.result.get(
                    "overpayment_amount"
                )
            )

            if not isinstance(
                order_id,
                int,
            ):
                continue

            if duplicate is not True:
                continue

            if not isinstance(
                overpayment,
                (
                    int,
                    float,
                ),
            ):
                continue

            facts[
                order_id
            ] = float(
                overpayment
            )

        return [
            (
                order_id,
                facts[order_id],
            )
            for order_id
            in sorted(
                facts
            )
        ]

    # -----------------------------------------------------
    # Answer fact matching
    # -----------------------------------------------------

    @staticmethod
    def _answer_mentions_order(
        answer: str,
        order_id: int,
    ) -> bool:
        """
        Require an explicit reference such as:

            Order 2
            Order ID 2
            Order #2

        This deliberately matches the same style expected
        by our current benchmark evaluator.
        """

        pattern = (
            r"\border"
            r"(?:\s+id)?"
            r"\s*[:#]?\s*"
            + re.escape(
                str(order_id)
            )
            + r"\b"
        )

        return (
            re.search(
                pattern,
                answer,
                flags=re.IGNORECASE,
            )
            is not None
        )

    @staticmethod
    def _answer_mentions_amount(
        answer: str,
        amount: float,
    ) -> bool:
        """
        Accept common numeric representations.

        Example for 39.90:

            39.90
            39.9
            $39.90
        """

        rounded = round(
            amount,
            2,
        )

        variants = {
            f"{rounded:.2f}",
            str(
                rounded
            ),
        }

        return any(
            variant in answer
            for variant in variants
        )

    # -----------------------------------------------------
    # Policy query
    # -----------------------------------------------------

    @staticmethod
    def _build_policy_query(
        user_request: str,
        duplicate_intent: bool,
    ) -> str:

        if duplicate_intent:

            return (
                "duplicate payment verification "
                "refund excess payment"
            )

        return (
            user_request
        )

    # -----------------------------------------------------
    # Trace helpers
    # -----------------------------------------------------

    @staticmethod
    def _find_successful_trace(
        tool_traces: list[
            ToolTraceLike
        ],
        tool_name: str,
        argument_name: str,
        argument_value: Any,
    ) -> ToolTraceLike | None:

        for trace in tool_traces:

            if trace.is_error:
                continue

            if (
                trace.tool_name
                != tool_name
            ):
                continue

            if (
                trace.arguments.get(
                    argument_name
                )
                == argument_value
            ):

                return trace

        return None

    @staticmethod
    def _order_ids_from_result(
        result: Any,
    ) -> set[int]:

        if not isinstance(
            result,
            dict,
        ):
            return set()

        orders = (
            result.get(
                "orders"
            )
        )

        if not isinstance(
            orders,
            list,
        ):
            return set()

        order_ids: set[
            int
        ] = set()

        for order in orders:

            if not isinstance(
                order,
                dict,
            ):
                continue

            order_id = (
                order.get(
                    "order_id"
                )
            )

            if isinstance(
                order_id,
                int,
            ):

                order_ids.add(
                    order_id
                )

        return order_ids

    # -----------------------------------------------------
    # Identifier extraction
    # -----------------------------------------------------

    @staticmethod
    def _extract_customer_id(
        text: str,
    ) -> int | None:

        match = re.search(
            (
                r"\bcustomer"
                r"(?:\s+id)?"
                r"\s*[:#]?\s*"
                r"(\d+)\b"
            ),
            text,
            flags=re.IGNORECASE,
        )

        if match is None:
            return None

        return int(
            match.group(1)
        )

    @staticmethod
    def _extract_order_ids(
        text: str,
    ) -> set[int]:

        matches = re.findall(
            (
                r"\border"
                r"(?:\s+id)?"
                r"\s*[:#]?\s*"
                r"(\d+)\b"
            ),
            text,
            flags=re.IGNORECASE,
        )

        return {
            int(value)
            for value
            in matches
        }

    # -----------------------------------------------------
    # Text helpers
    # -----------------------------------------------------

    @staticmethod
    def _contains_any(
        text: str,
        patterns: tuple[
            str,
            ...,
        ],
    ) -> bool:

        return any(
            pattern in text
            for pattern
            in patterns
        )

    @staticmethod
    def _answer_makes_policy_claim(
        answer_lower: str,
    ) -> bool:

        if "policy" in answer_lower:
            return True

        patterns = (
            "novashop says",
            "novashop requires",
            "novashop allows",
            "novashop does not allow",
            "according to novashop",
        )

        return any(
            pattern in answer_lower
            for pattern
            in patterns
        )

    # -----------------------------------------------------
    # Deduplication
    # -----------------------------------------------------

    @staticmethod
    def _deduplicate_issues(
        issues: list[
            VerificationIssue
        ],
    ) -> list[
        VerificationIssue
    ]:

        seen: set[
            tuple[str, str]
        ] = set()

        unique: list[
            VerificationIssue
        ] = []

        for issue in issues:

            key = (
                issue.code,
                issue.message,
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            unique.append(
                issue
            )

        return unique

    @staticmethod
    def _deduplicate_actions(
        actions: list[
            VerificationAction
        ],
    ) -> list[
        VerificationAction
    ]:

        seen: set[
            str
        ] = set()

        unique: list[
            VerificationAction
        ] = []

        for action in actions:

            fingerprint = (
                action.tool_name
                + ":"
                + json.dumps(
                    action.arguments,
                    sort_keys=True,
                    default=str,
                )
            )

            if fingerprint in seen:
                continue

            seen.add(
                fingerprint
            )

            unique.append(
                action
            )

        return unique
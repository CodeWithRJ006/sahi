import json
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict

# Import required SAHI components for deterministic demo
# Import required SAHI components for deterministic demo
from sahi.amounts.engine import AmountEngine
from sahi.guard.engine import SahiGuard, GuardDecision, ReasonCode

@dataclass
class Scenario:
    name: str
    language: str
    utterance: str
    intended_amount: int
    # Mock transcript and LLM proposal will be derived within the demo.

def run_demo() -> List[Dict]:
    scenarios = [
        Scenario(name="A_SUCCESS", language="Hindi", utterance="₹2500 भेजो", intended_amount=2500),
        Scenario(name="B_WRONG_AMOUNT", language="Telugu", utterance="₹5000 పంపించు", intended_amount=5000),
        Scenario(name="C_AMBIGUOUS", language="Hinglish", utterance="send 500 no wait 5000", intended_amount=0),
    ]

    results = []
    for sc in scenarios:
        # Create isolated mock bank ledger for this scenario
        from sahi.bank.database import MockBankDatabase
        bank = MockBankDatabase()
        # Deterministic mock outcome for the demo
        engine = AmountEngine()
        guard = SahiGuard()
        # Parse the utterance
        parsed = engine.parse(sc.utterance)
        # Determine LLM proposal based on scenario name (simulating a proposal)
        if sc.name == "A_SUCCESS":
            llm_proposal = sc.intended_amount
        elif sc.name == "B_WRONG_AMOUNT":
            llm_proposal = 50000
        else:
            llm_proposal = None
        # Evaluate guard decision using parsed amount and simulated LLM proposal
        guard_decision = guard.evaluate_parsed_amount(parsed, proposed_by_agent=llm_proposal)
        guard_action = guard_decision.action
        reason = guard_decision.reason_code


        # Ledger simple placeholder
        ledger_simple: List[Dict] = []
        if guard_decision.action.name == "EXECUTE":
            ledger_simple.append({"amount": sc.intended_amount, "utterance": sc.utterance})

        # Prepare outcome dict for test expectations
        outcome = {"parsed_amount": parsed.amount_inr if parsed.amount_inr is not None else None,
                   "llm_proposal": llm_proposal}
        # Ledger already serialized above (if any transfer occurred)
        # No further guard re-evaluation needed

        # Collect result summary
        result = {
            "scenario": sc.name,
            "utterance": sc.utterance,
            "intended_amount": sc.intended_amount,
            "parsed_amount": outcome.get("parsed_amount"),
            "llm_proposal": outcome.get("llm_proposal"),
            "guard_decision": guard_decision.action.name,
            "reason_code": reason.name if reason else None,
            "ledger": ledger_simple,
        }
        results.append(result)
    return results

def main():
    results = run_demo()
    # Pretty‑print to console
    print(json.dumps(results, indent=2, ensure_ascii=False))
    # Save deterministic JSON results for documentation / testing
    with open("demo_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

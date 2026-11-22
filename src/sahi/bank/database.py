"""SQLite database manager for the Mock Bank ledger with strict idempotency."""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sahi.bank.models import TransferRequest, TransferResponse, AccountBalance, TransactionRecord

class MockBankDatabase:
    """Thread-safe SQLite database manager for simulated banking ledger."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return self._conn

    def close(self):
        """Closes any active database connections."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    holder_name TEXT NOT NULL,
                    balance_inr INTEGER NOT NULL CHECK (balance_inr >= 0),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    idempotency_key TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    from_account TEXT NOT NULL,
                    to_payee TEXT NOT NULL,
                    amount_inr INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    guard_decision_json TEXT,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (from_account) REFERENCES accounts(account_id)
                );
            """)
            # Seed standard mock accounts if empty
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM accounts;")
            if cursor.fetchone()["cnt"] == 0:
                now = datetime.now(timezone.utc).isoformat()
                conn.executemany(
                    "INSERT INTO accounts (account_id, holder_name, balance_inr, created_at) VALUES (?, ?, ?, ?);",
                    [
                        ("ACC_USER_001", "Primary Test User", 100_000, now),
                        ("ACC_RAMESH_002", "Ramesh Kumar", 10_000, now),
                        ("ACC_SURESH_003", "Suresh Sharma", 5_000, now),
                    ]
                )
                conn.commit()

    def get_account(self, account_id: str) -> Optional[AccountBalance]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE account_id = ?;", (account_id,)).fetchone()
            if not row:
                return None
            return AccountBalance(
                account_id=row["account_id"],
                holder_name=row["holder_name"],
                balance_inr=row["balance_inr"],
                created_at=row["created_at"]
            )

    def list_transactions(self, limit: int = 50) -> List[TransactionRecord]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?;", (limit,)
            ).fetchall()
            results = []
            for r in rows:
                guard_dec = json.loads(r["guard_decision_json"]) if r["guard_decision_json"] else None
                results.append(
                    TransactionRecord(
                        transaction_id=r["transaction_id"],
                        from_account=r["from_account"],
                        to_payee=r["to_payee"],
                        amount_inr=r["amount_inr"],
                        status=r["status"],
                        guard_decision=guard_dec,
                        idempotency_key=r["idempotency_key"],
                        created_at=r["created_at"]
                    )
                )
            return results

    def execute_transfer(self, req: TransferRequest) -> TransferResponse:
        """
        Executes a transfer with atomic idempotency protection.
        If idempotency_key was already processed, returns cached response immediately.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            # 1. Check idempotency table first
            cur = conn.execute(
                "SELECT response_json FROM idempotency_keys WHERE idempotency_key = ?;",
                (req.idempotency_key,)
            )
            cached = cur.fetchone()
            if cached:
                cached_data = json.loads(cached["response_json"])
                cached_data["status"] = "IDEMPOTENT_DUPLICATE"
                cached_data["message"] = "Duplicate request with identical idempotency key returned from cache."
                return TransferResponse(**cached_data)

            # 2. Check source account balance
            acc_row = conn.execute(
                "SELECT balance_inr FROM accounts WHERE account_id = ?;",
                (req.from_account,)
            ).fetchone()

            if not acc_row:
                resp = TransferResponse(
                    success=False,
                    status="REJECTED",
                    transaction_id=None,
                    from_account=req.from_account,
                    to_payee=req.to_payee,
                    amount_inr=req.amount_inr,
                    new_balance_inr=None,
                    message=f"Source account {req.from_account} does not exist.",
                    idempotency_key=req.idempotency_key,
                    timestamp=now_iso
                )
                return resp

            current_balance = acc_row["balance_inr"]
            if current_balance < req.amount_inr:
                resp = TransferResponse(
                    success=False,
                    status="INSUFFICIENT_FUNDS",
                    transaction_id=None,
                    from_account=req.from_account,
                    to_payee=req.to_payee,
                    amount_inr=req.amount_inr,
                    new_balance_inr=current_balance,
                    message=f"Insufficient balance ({current_balance:,} INR) for transfer of {req.amount_inr:,} INR.",
                    idempotency_key=req.idempotency_key,
                    timestamp=now_iso
                )
                return resp

            # 3. Perform atomic deduction and transaction insert
            tx_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
            new_balance = current_balance - req.amount_inr
            guard_json = json.dumps(req.guard_decision) if req.guard_decision else None

            conn.execute(
                "UPDATE accounts SET balance_inr = ? WHERE account_id = ?;",
                (new_balance, req.from_account)
            )

            conn.execute(
                """
                INSERT INTO transactions (
                    transaction_id, from_account, to_payee, amount_inr, status,
                    guard_decision_json, idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (tx_id, req.from_account, req.to_payee, req.amount_inr, "SUCCESS", guard_json, req.idempotency_key, now_iso)
            )

            resp = TransferResponse(
                success=True,
                status="SUCCESS",
                transaction_id=tx_id,
                from_account=req.from_account,
                to_payee=req.to_payee,
                amount_inr=req.amount_inr,
                new_balance_inr=new_balance,
                message="Transfer executed successfully in mock ledger.",
                idempotency_key=req.idempotency_key,
                timestamp=now_iso
            )

            # Store in idempotency table
            conn.execute(
                "INSERT INTO idempotency_keys (idempotency_key, response_json, created_at) VALUES (?, ?, ?);",
                (req.idempotency_key, resp.model_dump_json(), now_iso)
            )

            conn.commit()
            return resp

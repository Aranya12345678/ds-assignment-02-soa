"""
SOAP Client - Fraud Detection Service
--------------------------------------
Author: Nikeshala Dewindi

This client is a legacy-style SOAP consumer. It talks ONLY to the Gateway's
SOAP endpoint (described by fraud_service.wsdl) -- it never talks to the
gRPC server directly. That's the whole point of the assignment: the client
doesn't know or care that gRPC exists behind the gateway.

It exercises every operation defined in the WSDL:
    1. CheckTransaction          -> normal + validation-error case
    2. FlagAccount                -> normal case
    3. GetAccountRiskProfile      -> normal + "not found" error case

Setup:
    pip install -r requirements.txt

Run (gateway must be running first, see gateway/README):
    python soap_client.py
"""

import sys
from datetime import datetime, timezone

from zeep import Client, Settings
from zeep.exceptions import Fault
from zeep.helpers import serialize_object

WSDL_PATH = "fraud_service.wsdl"          # local WSDL contract
GATEWAY_ENDPOINT = "http://localhost:8000/soap"  # override the WSDL's <soap:address> at runtime


def get_client() -> Client:
    """Build a SOAP client from the WSDL and point it at the running gateway."""
    settings = Settings(strict=False, xml_huge_tree=True)
    client = Client(WSDL_PATH, settings=settings)
    # The WSDL ships a default address; force it to the gateway we're actually running against.
    client.service._binding_options["address"] = GATEWAY_ENDPOINT
    return client


def pretty(title: str, obj) -> None:
    print(f"\n--- {title} ---")
    data = serialize_object(obj) if not isinstance(obj, dict) else obj
    for key, value in data.items():
        print(f"  {key}: {value}")


def call_check_transaction_ok(client: Client) -> None:
    """CheckTransaction - a normal, well-formed transaction."""
    try:
        response = client.service.CheckTransaction(
            transactionId="txn-1001",
            accountId="acc-2001",
            amount=250.00,
            currency="USD",
            merchantName="Amazon",
            timestamp=datetime.now(timezone.utc),
        )
        pretty("CheckTransaction (valid)", response)
    except Fault as fault:
        print_fault("CheckTransaction (valid)", fault)


def call_check_transaction_invalid_amount(client: Client) -> None:
    """CheckTransaction - negative amount should trigger a mapped SOAP Fault
    (gateway maps gRPC INVALID_ARGUMENT -> soap:Client fault)."""
    try:
        response = client.service.CheckTransaction(
            transactionId="txn-1002",
            accountId="acc-2001",
            amount=-50.00,
            currency="USD",
            merchantName="Unknown Merchant",
            timestamp=datetime.now(timezone.utc),
        )
        pretty("CheckTransaction (invalid amount) - unexpected success", response)
    except Fault as fault:
        print_fault("CheckTransaction (invalid amount, expected FAULT)", fault)


def call_flag_account(client: Client) -> None:
    """FlagAccount - normal case."""
    try:
        response = client.service.FlagAccount(
            accountId="acc-2001",
            reason="Multiple high-risk transactions in short window",
            flaggedBy="fraud-analyst-01",
        )
        pretty("FlagAccount", response)
    except Fault as fault:
        print_fault("FlagAccount", fault)


def call_get_account_risk_profile_ok(client: Client) -> None:
    """GetAccountRiskProfile - existing account."""
    try:
        response = client.service.GetAccountRiskProfile(accountId="acc-2001")
        pretty("GetAccountRiskProfile (existing account)", response)
    except Fault as fault:
        print_fault("GetAccountRiskProfile (existing account)", fault)


def call_get_account_risk_profile_not_found(client: Client) -> None:
    """GetAccountRiskProfile - unknown account should trigger a mapped SOAP
    Fault (gateway maps gRPC NOT_FOUND -> soap:Server fault)."""
    try:
        response = client.service.GetAccountRiskProfile(accountId="acc-does-not-exist")
        pretty("GetAccountRiskProfile (unknown account) - unexpected success", response)
    except Fault as fault:
        print_fault("GetAccountRiskProfile (unknown account, expected FAULT)", fault)


def print_fault(title: str, fault: Fault) -> None:
    print(f"\n--- {title} ---")
    print(f"  faultcode:   {fault.code}")
    print(f"  faultstring: {fault.message}")
    if fault.detail is not None:
        # fault.detail is an lxml Element containing tns:FraudServiceFaultDetail
        grpc_code = fault.detail.findtext(
            ".//{http://ds-assignment.example.com/fraud}grpcStatusCode"
        )
        grpc_msg = fault.detail.findtext(
            ".//{http://ds-assignment.example.com/fraud}grpcStatusMessage"
        )
        print(f"  grpcStatusCode:    {grpc_code}")
        print(f"  grpcStatusMessage: {grpc_msg}")


def main() -> int:
    try:
        client = get_client()
    except Exception as exc:  # noqa: BLE001 - top-level CLI entry point
        print(f"Failed to load WSDL '{WSDL_PATH}': {exc}")
        return 1

    print(f"Connected to gateway at {GATEWAY_ENDPOINT}")
    print("Running all Fraud Detection SOAP operations...")

    try:
        call_check_transaction_ok(client)
        call_check_transaction_invalid_amount(client)
        call_flag_account(client)
        call_get_account_risk_profile_ok(client)
        call_get_account_risk_profile_not_found(client)
    except Exception as exc:  # noqa: BLE001
        # Most likely a connection error because the gateway isn't running.
        print(f"\nCould not reach the gateway at {GATEWAY_ENDPOINT}: {exc}")
        print("Make sure the Gateway service is running before running this client.")
        return 1

    print("\nAll operations attempted. See output above for results/faults.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

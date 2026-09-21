"""
Gateway Test Script - Raw SOAP Requests
----------------------------------------
Author: Nikeshala Dewindi

Independent verification of the Gateway's SOAP endpoint.
"""

import requests
from lxml import etree

GATEWAY_URL = "http://localhost:8000/soap"
FRAUD_NS = "http://ds-assignment.example.com/fraud"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"


def send(xml_body: str):
    """POST raw SOAP XML to the Gateway and return the parsed lxml root."""
    response = requests.post(
        GATEWAY_URL,
        data=xml_body.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8"},
    )
    root = etree.fromstring(response.content)
    return response.status_code, root


def get_text(root, tag):
    el = root.find(f".//{{{FRAUD_NS}}}{tag}")
    return el.text if el is not None else None


def print_response(title, status, root):
    print(f"\n--- {title} (HTTP {status}) ---")
    fault = root.find(f".//{{{SOAP_NS}}}Fault")
    if fault is not None:
        faultcode = fault.findtext("faultcode")
        faultstring = fault.findtext("faultstring")
        grpc_code = root.find(f".//{{{FRAUD_NS}}}grpcStatusCode")
        grpc_msg = root.find(f".//{{{FRAUD_NS}}}grpcStatusMessage")
        print(f"    FAULT    faultcode={faultcode}    faultstring={faultstring}")
        print(f"             grpcStatusCode={grpc_code.text if grpc_code is not None else None}")
        print(f"             grpcStatusMessage={grpc_msg.text if grpc_msg is not None else None}")
    else:
        body = root.find(f".//{{{SOAP_NS}}}Body")
        response_el = body[0]
        for child in response_el:
            tag = etree.QName(child).localname
            print(f"    {tag}: {child.text}")


# --- Test Payloads ---

check_transaction_valid = f"""
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:fraud="{FRAUD_NS}">
    <soapenv:Body>
        <fraud:CheckTransactionRequest>
            <fraud:transactionId>txn-raw-001</fraud:transactionId>
            <fraud:accountId>acc-2001</fraud:accountId>
            <fraud:amount>180.00</fraud:amount>
            <fraud:currency>USD</fraud:currency>
            <fraud:merchantName>Raw Test Merchant</fraud:merchantName>
            <fraud:timestamp>2026-09-21T09:00:00+00:00</fraud:timestamp>
        </fraud:CheckTransactionRequest>
    </soapenv:Body>
</soapenv:Envelope>
"""

check_transaction_invalid = f"""
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:fraud="{FRAUD_NS}">
    <soapenv:Body>
        <fraud:CheckTransactionRequest>
            <fraud:transactionId>txn-raw-002</fraud:transactionId>
            <fraud:accountId>acc-2001</fraud:accountId>
            <fraud:amount>-10.00</fraud:amount>
            <fraud:currency>USD</fraud:currency>
            <fraud:merchantName>Raw Test Merchant</fraud:merchantName>
            <fraud:timestamp>2026-09-21T09:01:00+00:00</fraud:timestamp>
        </fraud:CheckTransactionRequest>
    </soapenv:Body>
</soapenv:Envelope>
"""

flag_account = f"""
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:fraud="{FRAUD_NS}">
    <soapenv:Body>
        <fraud:FlagAccountRequest>
            <fraud:accountId>acc-2001</fraud:accountId>
            <fraud:reason>Raw SOAP test - flagging for verification</fraud:reason>
            <fraud:flaggedBy>gateway-test-script</fraud:flaggedBy>
        </fraud:FlagAccountRequest>
    </soapenv:Body>
</soapenv:Envelope>
"""

risk_profile_existing = f"""
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:fraud="{FRAUD_NS}">
    <soapenv:Body>
        <fraud:GetAccountRiskProfileRequest>
            <fraud:accountId>acc-2001</fraud:accountId>
        </fraud:GetAccountRiskProfileRequest>
    </soapenv:Body>
</soapenv:Envelope>
"""

risk_profile_unknown = f"""
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:fraud="{FRAUD_NS}">
    <soapenv:Body>
        <fraud:GetAccountRiskProfileRequest>
            <fraud:accountId>acc-raw-does-not-exist</fraud:accountId>
        </fraud:GetAccountRiskProfileRequest>
    </soapenv:Body>
</soapenv:Envelope>
"""


def main():
    print(f"Sending raw SOAP requests to {GATEWAY_URL}")
    tests = [
        ("CheckTransaction (valid)", check_transaction_valid),
        ("CheckTransaction (invalid amount, expect FAULT)", check_transaction_invalid),
        ("FlagAccount", flag_account),
        ("GetAccountRiskProfile (existing account)", risk_profile_existing),
        ("GetAccountRiskProfile (unknown account, expect FAULT)", risk_profile_unknown),
    ]

    for title, xml_body in tests:
        try:
            status, root = send(xml_body)
            print_response(title, status, root)
        except requests.exceptions.ConnectionError:
            print(f"\nCould not reach the Gateway at {GATEWAY_URL}.")
            print("Make sure both the gRPC server and the Gateway are running.")
            return

    print("\nAll raw SOAP requests attempted. See results above.")


if __name__ == "__main__":
    main()

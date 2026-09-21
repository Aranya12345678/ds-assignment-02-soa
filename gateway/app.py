import os
from flask import Flask, request, Response
from lxml import etree
import grpc

import fraud_pb2
import fraud_pb2_grpc

app = Flask(__name__)

# --- namespaces used throughout the SOAP messages ---
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
FRAUD_NS = "http://ds-assignment.example.com/fraud"
NSMAP = {"soap-env": SOAP_NS, "tns": FRAUD_NS}

# --- connect to the gRPC server once, reused for every request ---
grpc_channel = grpc.insecure_channel('localhost:50051')
grpc_stub = fraud_pb2_grpc.FraudDetectionServiceStub(grpc_channel)


def parse_soap_request(xml_bytes):
    """Parse incoming SOAP XML, return (operation_name, body_element)."""
    root = etree.fromstring(xml_bytes)
    body = root.find(f"{{{SOAP_NS}}}Body")
    if body is None or len(body) == 0:
        raise ValueError("Invalid SOAP envelope: Missing Body element")
    operation_element = body[0]
    tag_without_ns = etree.QName(operation_element).localname
    return tag_without_ns, operation_element


def get_field(element, field_name):
    """Read a single field's text value from a request element."""
    child = element.find(f"{{{FRAUD_NS}}}{field_name}")
    return child.text if child is not None else None


def build_soap_response(response_element):
    """Wrap a response element in a full SOAP envelope."""
    envelope = etree.Element(f"{{{SOAP_NS}}}Envelope", nsmap=NSMAP)
    body = etree.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    body.append(response_element)
    return etree.tostring(envelope, xml_declaration=True, encoding="UTF-8")


def build_soap_fault(grpc_status_code, grpc_message):
    """Build a SOAP Fault matching the WSDL's FraudServiceFaultDetail shape with comprehensive status code mapping."""
    envelope = etree.Element(f"{{{SOAP_NS}}}Envelope", nsmap=NSMAP)
    body = etree.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    fault = etree.SubElement(body, f"{{{SOAP_NS}}}Fault")

    # Client-side errors map to soap:Client; server/system errors map to soap:Server
    client_errors = [
        grpc.StatusCode.INVALID_ARGUMENT,
        grpc.StatusCode.NOT_FOUND,
        grpc.StatusCode.ALREADY_EXISTS,
        grpc.StatusCode.UNAUTHENTICATED,
        grpc.StatusCode.PERMISSION_DENIED,
        grpc.StatusCode.OUT_OF_RANGE,
    ]

    if grpc_status_code in client_errors:
        faultcode = "soap:Client"
    else:
        faultcode = "soap:Server"

    etree.SubElement(fault, "faultcode").text = faultcode
    etree.SubElement(fault, "faultstring").text = str(grpc_message)

    detail = etree.SubElement(fault, "detail")
    fault_detail = etree.SubElement(detail, f"{{{FRAUD_NS}}}FraudServiceFaultDetail", nsmap=NSMAP)
    code_name = grpc_status_code.name if hasattr(grpc_status_code, 'name') else str(grpc_status_code)
    etree.SubElement(fault_detail, f"{{{FRAUD_NS}}}grpcStatusCode").text = code_name
    etree.SubElement(fault_detail, f"{{{FRAUD_NS}}}grpcStatusMessage").text = str(grpc_message)

    return etree.tostring(envelope, xml_declaration=True, encoding="UTF-8")


def handle_check_transaction(request_element):
    transaction_id = get_field(request_element, "transactionId")
    account_id = get_field(request_element, "accountId")
    
    raw_amount = get_field(request_element, "amount")
    amount = float(raw_amount) if raw_amount is not None else 0.0
    
    merchant_name = get_field(request_element, "merchantName") or ""
    timestamp = get_field(request_element, "timestamp") or ""

    grpc_request = fraud_pb2.TransactionRequest(
        transaction_id=transaction_id or "",
        account_id=account_id or "",
        amount=amount,
        merchant=merchant_name,
        timestamp=timestamp,
    )
    grpc_response = grpc_stub.CheckTransaction(grpc_request)

    response_element = etree.Element(f"{{{FRAUD_NS}}}CheckTransactionResponse", nsmap=NSMAP)
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}transactionId").text = transaction_id or ""
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}decision").text = grpc_response.decision
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}riskScore").text = str(grpc_response.risk_score)
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}reason").text = ", ".join(grpc_response.reason_codes) or "OK"

    return response_element


def handle_flag_account(request_element):
    account_id = get_field(request_element, "accountId") or ""
    reason = get_field(request_element, "reason") or ""
    flagged_by = get_field(request_element, "flaggedBy") or ""

    grpc_request = fraud_pb2.FlagAccountRequest(
        account_id=account_id,
        reason=reason,
        flagged_by=flagged_by,
    )
    grpc_response = grpc_stub.FlagAccount(grpc_request)

    response_element = etree.Element(f"{{{FRAUD_NS}}}FlagAccountResponse", nsmap=NSMAP)
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}success").text = str(grpc_response.success).lower()
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}message").text = grpc_response.message

    return response_element


def handle_get_account_risk_profile(request_element):
    account_id = get_field(request_element, "accountId") or ""

    grpc_request = fraud_pb2.RiskProfileRequest(
        account_id=account_id,
    )
    grpc_response = grpc_stub.GetAccountRiskProfile(grpc_request)

    # WSDL wants a numeric riskScore; gRPC gives a risk_level string -> derive one
    risk_score_map = {"LOW": 0.2, "MEDIUM": 0.5, "HIGH": 0.8}
    risk_score = risk_score_map.get(grpc_response.risk_level, 0.0)

    response_element = etree.Element(f"{{{FRAUD_NS}}}GetAccountRiskProfileResponse", nsmap=NSMAP)
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}accountId").text = account_id
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}riskLevel").text = grpc_response.risk_level
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}riskScore").text = str(risk_score)
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}flagCount").text = str(len(grpc_response.recent_flags))
    etree.SubElement(response_element, f"{{{FRAUD_NS}}}lastUpdated").text = grpc_response.last_reviewed_date

    return response_element


@app.route('/soap', methods=['GET'])
def get_wsdl():
    """Serve the WSDL definition directly from the Gateway."""
    possible_paths = [
        'fraud_service.wsdl',
        os.path.join(os.path.dirname(__file__), 'fraud_service.wsdl'),
        os.path.join(os.path.dirname(__file__), '..', 'soap-client', 'fraud_service.wsdl')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                wsdl_content = f.read()
            return Response(wsdl_content, mimetype='text/xml')
            
    return Response("WSDL specification file not found on gateway server", status=404)


@app.route('/soap', methods=['POST'])
def soap_endpoint():
    try:
        operation_name, request_element = parse_soap_request(request.data)
        print(f"Received operation: {operation_name}")

        if operation_name == "CheckTransactionRequest":
            response_element = handle_check_transaction(request_element)
        elif operation_name == "FlagAccountRequest":
            response_element = handle_flag_account(request_element)
        elif operation_name == "GetAccountRiskProfileRequest":
            response_element = handle_get_account_risk_profile(request_element)
        else:
            fault_xml = build_soap_fault(grpc.StatusCode.INVALID_ARGUMENT, f"Unknown operation: {operation_name}")
            return Response(fault_xml, mimetype='text/xml', status=400)

        response_xml = build_soap_response(response_element)
        return Response(response_xml, mimetype='text/xml')

    except grpc.RpcError as e:
        print(f"gRPC error: {e.code()} - {e.details()}")
        fault_xml = build_soap_fault(e.code(), e.details())
        return Response(fault_xml, mimetype='text/xml', status=500)
    except Exception as e:
        print(f"Gateway internal error: {str(e)}")
        fault_xml = build_soap_fault(grpc.StatusCode.INTERNAL, str(e))
        return Response(fault_xml, mimetype='text/xml', status=500)


if __name__ == '__main__':
    app.run(port=8000, debug=True)

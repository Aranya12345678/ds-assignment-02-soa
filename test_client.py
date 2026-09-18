import grpc
import fraud_pb2
import fraud_pb2_grpc

def run():
    # Connect to the server we started (same machine, port 50051)
    channel = grpc.insecure_channel('localhost:50051')
    stub = fraud_pb2_grpc.FraudDetectionServiceStub(channel)

    # Test 1: CheckTransaction (normal case)
    response = stub.CheckTransaction(fraud_pb2.TransactionRequest(
        transaction_id="tx001",
        account_id="acc123",
        amount=500.0,
        merchant="Amazon",
        timestamp="2026-09-18T10:00:00Z"
    ))
    print("CheckTransaction response:")
    print(response)

    # Test 2: FlagAccount
    response = stub.FlagAccount(fraud_pb2.FlagAccountRequest(
        account_id="acc123",
        reason="Suspicious login pattern",
        flagged_by="admin"
    ))
    print("FlagAccount response:")
    print(response)

    # Test 3: GetAccountRiskProfile
    response = stub.GetAccountRiskProfile(fraud_pb2.RiskProfileRequest(
        account_id="acc123"
    ))
    print("GetAccountRiskProfile response:")
    print(response)

    # Test 4: CheckTransaction with invalid amount (should trigger an error)
    try:
        response = stub.CheckTransaction(fraud_pb2.TransactionRequest(
            transaction_id="tx002",
            account_id="acc123",
            amount=-50.0,
            merchant="Amazon",
            timestamp="2026-09-18T10:00:00Z"
        ))
        print("Test 4 response:", response)
    except grpc.RpcError as e:
        print(f"Test 4 - Got expected error: {e.code()} - {e.details()}")

    # Test 5: GetAccountRiskProfile with unknown account (should trigger NOT_FOUND)
    try:
        response = stub.GetAccountRiskProfile(fraud_pb2.RiskProfileRequest(
            account_id="unknown"
        ))
        print("Test 5 response:", response)
    except grpc.RpcError as e:
        print(f"Test 5 - Got expected error: {e.code()} - {e.details()}")


if __name__ == '__main__':
    run()
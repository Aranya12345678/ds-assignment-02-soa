from concurrent import futures
import grpc

import fraud_pb2
import fraud_pb2_grpc

class FraudDetectionServicer(fraud_pb2_grpc.FraudDetectionServiceServicer):

    def CheckTransaction(self, request, context):
        # Basic input validation
        if request.amount <= 0:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Amount must be greater than zero")
            return fraud_pb2.TransactionResponse()

        # Simple fraud logic (placeholder — make it as fancy as you like)
        if request.amount > 10000:
            decision = "DECLINE"
            risk_score = 0.9
            reasons = ["high_amount"]
        elif request.amount > 1000:
            decision = "REVIEW"
            risk_score = 0.5
            reasons = ["moderate_amount"]
        else:
            decision = "APPROVE"
            risk_score = 0.1
            reasons = []

        return fraud_pb2.TransactionResponse(
            risk_score=risk_score,
            decision=decision,
            reason_codes=reasons
        )

    def FlagAccount(self, request, context):
        # Basic input validation
        if not request.account_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("account_id is required")
            return fraud_pb2.FlagAccountResponse()

        # Placeholder logic
        print(f"Account {request.account_id} flagged by {request.flagged_by}: {request.reason}")

        return fraud_pb2.FlagAccountResponse(
            success=True,
            message="Account flagged successfully"
        )

    def GetAccountRiskProfile(self, request, context):
        # Basic input validation
        if not request.account_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("account_id is required")
            return fraud_pb2.RiskProfileResponse()

        # Placeholder
        if request.account_id == "unknown":
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Account {request.account_id} not found")
            return fraud_pb2.RiskProfileResponse()

        return fraud_pb2.RiskProfileResponse(
            risk_level="LOW",
            recent_flags=[],
            last_reviewed_date="2026-09-01"
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    fraud_pb2_grpc.add_FraudDetectionServiceServicer_to_server(
        FraudDetectionServicer(), server
    )
    server.add_insecure_port('[::]:50051')
    print("gRPC server starting on port 50051...")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
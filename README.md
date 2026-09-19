# Distributed Systems Assignment 02 — SOA Legacy System (Banking)

A small distributed system where a SOAP client talks to a gRPC-based Fraud Detection service through a translating gateway.

## Scenario

A legacy core banking system (SOAP/XML-based) needs to consume a modern gRPC-based Fraud Detection microservice for real-time transaction risk checks. A gateway translates between the two protocols.

## Components

1. **gRPC Fraud Detection Server** ✅ *(done)*
   - Location: root folder (`server.py`, `fraud.proto`, generated `fraud_pb2*.py`)
   - Operations: `CheckTransaction`, `FlagAccount`, `GetAccountRiskProfile`
2. **Gateway** — not started yet
3. **SOAP Client** — not started yet

## Setup & Run — gRPC Server

1. Create and activate a virtual environment:

       python -m venv venv
       venv\Scripts\activate

2. Install dependencies:

       pip install grpcio grpcio-tools

3. (Only needed if you edit `fraud.proto`) Regenerate code:

       python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. fraud.proto

4. Run the server:

       python server.py

   Server listens on `localhost:50051`.

## Testing

A test client (`test_client.py`) exercises all 3 operations plus 2 error cases (invalid amount, unknown account).

With the server running, in a separate terminal:

    venv\Scripts\activate
    python test_client.py

Expected: 3 successful responses (APPROVE decision, flag confirmation, risk profile), plus 2 caught `grpc.RpcError`s (`INVALID_ARGUMENT`, `NOT_FOUND`).

## Team

- Aranya Wijayasekara — gRPC server
- Nikeshala Dewindi — SOAP client
- Both — Gateway

  ## Setup & Run — SOAP Client (Nikeshala Dewindi)
1. Navigate to the client folder:
   cd soap-client

2. Install dependencies:
   pip install -r requirements.txt

3. Ensure the Translating Gateway is running at http://localhost:8000/soap.

4. Run the SOAP client test suite:
   python soap_client.py

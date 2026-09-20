# Distributed Systems Assignment 02 — SOA Legacy System (Banking)

A small distributed system where a SOAP client talks to a gRPC-based Fraud Detection service through a translating gateway.

## Scenario

A legacy core banking system (SOAP/XML-based) needs to consume a modern gRPC-based Fraud Detection microservice for real-time transaction risk checks. A gateway translates between the two protocols, including real field-level translation and bidirectional error/fault mapping.

## Components

1. **gRPC Fraud Detection Server** ✅
   - Location: root folder (`server.py`, `fraud.proto`, generated `fraud_pb2*.py`)
   - Operations: `CheckTransaction`, `FlagAccount`, `GetAccountRiskProfile`
   - Basic input validation with proper gRPC status codes (`INVALID_ARGUMENT`, `NOT_FOUND`)

2. **Gateway** ✅
   - Location: `gateway/` (`app.py`, plus copied `fraud_pb2*.py`)
   - Exposes a SOAP endpoint at `http://localhost:8000/soap`, matching `soap-client/fraud_service.wsdl`
   - Real translation logic: field renaming (e.g. `merchantName` -> `merchant`), computed fields (e.g. `riskScore` derived from `riskLevel`, `flagCount` from list length), list-to-string joining (`reason_codes` -> `reason`)
   - Maps gRPC status codes to SOAP faults (`INVALID_ARGUMENT` -> `soap:Client`, `NOT_FOUND` -> `soap:Server`), carrying the original gRPC code/message in the fault detail

3. **SOAP Client** ✅
   - Location: `soap-client/` (`soap_client.py`, `fraud_service.wsdl`)
   - Exercises every operation, including error cases

## Setup

1. Create and activate a virtual environment (once, at project root):

       python -m venv venv
       venv\Scripts\activate        # Windows

2. Install all dependencies:

       pip install grpcio grpcio-tools flask lxml
       pip install -r soap-client\requirements.txt

3. (Only needed if you edit `fraud.proto`) Regenerate gRPC code, then copy into `gateway/`:

       python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. fraud.proto
       copy fraud_pb2.py gateway\
       copy fraud_pb2_grpc.py gateway\

## Running

**Quick start:** run `start_services.bat` from the project root — this opens the gRPC server and Gateway in separate windows automatically.

**Manual start** (3 terminals, all with `venv` activated):

1. gRPC Server (project root):

       python server.py

   Listens on `localhost:50051`.

2. Gateway (`gateway/` folder):

       cd gateway
       python app.py

   Listens on `localhost:8000/soap`.

3. SOAP Client (`soap-client/` folder), once both above are running:

       cd soap-client
       python soap_client.py

## Testing

`soap_client.py` exercises all 3 operations plus error cases:
- `CheckTransaction` — valid case, and invalid amount (expects `soap:Client` fault)
- `FlagAccount` — valid case
- `GetAccountRiskProfile` — existing account, and unknown account (expects `soap:Server` fault)

Expected output: 3 successful SOAP responses, plus 2 properly mapped SOAP faults showing the original gRPC status code and message in the fault detail.

There's also `test_client.py` at the project root — a standalone script that talks directly to the gRPC server (bypassing SOAP/Gateway), used during development to verify server logic in isolation.

## Known issues / troubleshooting

- If you see "address already in use" when starting the gRPC server, an old instance is likely still running. Check with `netstat -ano | findstr :50051` (or `tasklist | findstr python`) and stop the leftover process before restarting.
- Each service (gRPC server, Gateway) must be started in its own terminal window and left running; only the SOAP client is meant to be re-run on demand.

## Team

- Aranya Wijayasekara — gRPC server, Gateway
- Nikeshala Dewindi — SOAP client, Gateway
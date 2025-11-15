# ZULU Architecture Diagram

```mermaid
graph TB
    subgraph User_Device["User/Merchant Device"]
        direction TB
        
        subgraph Frontend["Frontend (React/Next.js)"]
            UI[User Interface]
            Chat[AI Chat Component]
            Terminal[Merchant Terminal]
            QR[QR Code Generator]
        end
        
        subgraph Backend["ZULU Backend (Node.js)"]
            API[API Server]
            
            subgraph AI_Engine["AI Engine"]
                Ollama[Ollama Client]
                Phi3[Phi-3 Mini Model]
                QueryEngine[NL → SQL Query Engine]
            end
            
            subgraph Ledger["Encrypted Ledger"]
                SQLCipher[(SQLCipher DB)]
                TxStore[Transaction Store]
                InvoiceStore[Invoice Store]
            end
            
            subgraph ZEC_Module["Zcash Module"]
                LWD_Client[Lightwalletd Client]
                TxWatcher[Transaction Watcher]
                ViewKey[View Key Manager]
            end
            
            subgraph NEAR_Module["NEAR Swap Engine"]
                SwapClient[NEAR RPC Client]
                SwapRouter[Swap Router]
                SettlementTracker[Settlement Tracker]
            end
            
            subgraph Utils["Utilities"]
                PriceOracle[Price Oracle]
                SafetyChecks[Safety Checks]
                Logger[Logger]
            end
        end
    end
    
    subgraph External_Services["External Services"]
        LWD[Lightwalletd Node<br/>Zcash Network]
        NEAR_RPC[NEAR RPC<br/>Testnet/Mainnet]
        NEAR_Contract[NEAR Swap Contract<br/>ZEC → USDC]
        PriceAPI[CoinGecko API<br/>Price Data]
    end
    
    subgraph Merchant_Settlement["Merchant Settlement"]
        USDC_Account[Merchant USDC Account]
        Dashboard[Merchant Dashboard]
    end
    
    %% User Flow
    UI --> API
    Chat --> API
    Terminal --> API
    
    %% API to Modules
    API --> AI_Engine
    API --> Ledger
    API --> ZEC_Module
    API --> NEAR_Module
    API --> Utils
    
    %% AI Flow
    QueryEngine --> SQLCipher
    Ollama --> Phi3
    
    %% ZEC Flow
    LWD_Client --> LWD
    TxWatcher --> ViewKey
    ViewKey --> SQLCipher
    
    %% NEAR Flow
    SwapRouter --> NEAR_RPC
    NEAR_RPC --> NEAR_Contract
    NEAR_Contract --> USDC_Account
    
    %% Price Flow
    PriceOracle --> PriceAPI
    
    %% QR Generation Flow
    QR --> Terminal
    Terminal --> InvoiceStore
    
    %% Settlement Flow
    SettlementTracker --> Dashboard
    
    %% Styling
    classDef private fill:#2d3748,stroke:#F4B728,stroke-width:2px,color:#fff
    classDef external fill:#1a202c,stroke:#A855F7,stroke-width:2px,color:#fff
    classDef secure fill:#1e3a8a,stroke:#06B6D4,stroke-width:2px,color:#fff
    
    class Frontend,Backend,AI_Engine,Ledger private
    class External_Services,LWD,NEAR_RPC,NEAR_Contract external
    class SQLCipher,ViewKey,Phi3 secure
```

## Component Descriptions

### Frontend Components

**User Interface**
- Main application interface
- Merchant and user views
- Real-time payment status

**AI Chat Component**
- Natural language interface
- Query history
- Response formatting

**Merchant Terminal**
- Invoice generation
- Payment detection
- Settlement tracking

**QR Code Generator**
- Creates payment QRs
- Encodes amount and address
- Display and sharing

### Backend Modules

**AI Engine**
- Runs Phi-3 Mini locally via Ollama
- Converts natural language to SQL
- Generates insights and summaries
- No cloud inference

**Encrypted Ledger**
- SQLCipher-encrypted database
- Stores transaction metadata
- Merchant invoices and settlements
- Pricing snapshots

**Zcash Module**
- Connects to lightwalletd
- Watch-only via viewing keys
- Detects shielded transactions
- No private key access

**NEAR Swap Engine**
- Interfaces with NEAR contracts
- Routes ZEC → USDC swaps
- Tracks settlement status
- Non-custodial design

**Utilities**
- Price oracle (CoinGecko)
- Safety and risk checks
- Logging and monitoring
- Configuration management

### Data Flow

**User Payment Flow**
1. User scans merchant QR code
2. ZULU displays ZEC equivalent
3. User pays from their wallet
4. TxWatcher detects shielded payment
5. ZULU records in encrypted ledger
6. (Optional) Triggers NEAR swap
7. Merchant receives USDC

**AI Query Flow**
1. User asks question in natural language
2. Query engine converts to SQL
3. Queries encrypted local ledger
4. Returns formatted response
5. All processing stays on-device

**Privacy Guarantees**
- ✅ No private keys ever imported
- ✅ No cloud AI inference
- ✅ Encrypted local storage
- ✅ View-only Zcash access
- ✅ Non-custodial swap routing

## Security Boundaries

**Local Boundary** (Green)
- All user data stays within device
- Encrypted at rest
- No telemetry or logging

**External Services** (Purple)
- Minimal metadata exposure
- Standard RPC calls only
- No sensitive data shared

**Secure Components** (Blue)
- Encrypted database
- View key isolation
- Local AI model

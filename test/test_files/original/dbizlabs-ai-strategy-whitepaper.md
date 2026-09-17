# DBizLabs AI Strategy 2026-2028: Agentic Systems, Domain-Specific RAG, and Trust

**Publication Date:** 1 October 2026 (Internal Whitepaper - Confidential Tier 2)
**Author:** Amala Appathurai, Chief Technology Officer
**Contributors:** Narmadha Sivakumar (CPO), Karthiga Rajoo (CFO), Dr. Sujatha Raman (Principal AI Safety Researcher), Santhana Krishnan (Head of Legal / DPO)
**Classification:** Confidential Tier 2. For internal distribution to employees and Board of Directors. For external distribution only with written CTO sign-off.

---

## 1. Executive Summary

Over the three-year period FY2027-FY2029 (calendar 2026 Q4 through 2028 Q4), DBizLabs will invest approximately S$34.8 million in research, development, governance, and infrastructure to realise the vision set out in this document: to make DBiz GPT - the AI platform powering Meiji MES, Bond Copilot, and Hirethm - the most trusted, most domain-capable, and most agentic enterprise AI platform in our three target verticals.

The strategy rests on three mutually reinforcing strategic pillars:

1. **Pillar 1 - Agentic Copilot Architecture:** Evolve our current RAG-centric chat interactions into a full agentic system where the AI platform is not merely an answer engine but an autonomous collaborator that plans, calls tools, orchestrates sub-agents, and executes multi-step workflows on behalf of the user. By the end of 2028 we target 40+ production agents deployed across all three product lines, with a tool-use success rate of 90% or higher.

2. **Pillar 2 - Domain-Specific Hybrid RAG:** Deepen the structural advantages we have built in retrieval-augmented generation by industrialising a hybrid vector + keyword stack, purpose-built chunking strategies per document class, fine-tuned multilingual embeddings, and a rigorous evaluation harness covering 12 document types and more than 2,400 golden QA pairs. We target a 92% faithfulness score on RAG answers by Q4 FY2027 and sustain it through the strategy horizon.

3. **Pillar 3 - Governance, Safety, and Evaluations:** Build, formalise, and certify a first-in-class enterprise AI governance and safety regime that is compliant with the Singapore AI Governance Act (effective 1 February 2027), aligned with the EU AI Act, and independently auditable. We will obtain SOC 2 Type II (May 2027), ISO 27001 (December 2027), and the SG AI Governance Trustmark (June 2028).

These three pillars are delivered on a foundation of **three-region security and data residency**, an **open-source-first engineering operating model**, and a **target KPI framework** that ties every AI programme to measurable business outcomes. By FY2028 we target that 30% or more of new ACV bookings is directly attributable to AI-embedded features and agentic workflows.

This whitepaper is the authoritative reference for AI strategy across DBizLabs. All product, engineering, design, security, legal, and go-to-market plans for FY2027-FY2029 should be explicitly mapped to the pillars and KPIs described herein.

---

## 2. Why Now: The Confluence of Technology, Regulation, and Customer Demand

Three converging forces make the 2026-2028 window both the opportunity and the imperative for decisive investment in AI at DBizLabs.

**First - the technology frontier has crossed a critical threshold for agentic enterprise systems.** As recently as 2024, enterprise LLMs could reliably answer single-turn questions grounded in retrieved context, but they struggled with the multi-step planning, tool calling, and error recovery required for true workflow automation. Today in Q3 FY2026, frontier models (GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro) and orchestration frameworks (LangGraph, the Open WebUI Agents SDK, the Model Context Protocol) have together raised reliability to the point where targeted agent deployments are economically viable. Our internal benchmarks show a 79.6% task completion rate on Agentic Copilot v1.1 QA builds, vs. 51% 18 months ago. We believe the next 24 months will see reliability cross the 90% threshold where agentic systems become the default user interface for complex knowledge work in manufacturing, fixed-income finance, and HR.

**Second - the regulatory picture is clarifying, and first movers will turn compliance into competitive advantage.** The Singapore AI Governance Act received Royal Assent on 20 November 2025 and comes into force on 1 February 2027 with a 12-month transition period. The EU AI Act is in its application phase with most provisions becoming operational between 2026 and 2028. Many customers, particularly in financial services and the public sector, are already asking for evidence of Tier-classification, conformity assessments, and AI TRiSM (Trust, Risk and Security Management) controls as pre-qualification to bid. DBizLabs' decision to build a full AI Governance Council, internal red team, and model registry now is not just compliance cost - it is a go-to-market accelerator, because our competitors are still treating this as a 2028 problem.

**Third - customer demand is shifting from "show me a demo" to "give me measurable ROI and safety guarantees."** Over the past 18 months the conversation in sales cycles has evolved dramatically. In FY2025, 70% of Bond Copilot discovery calls started with "what model do you use?" Today 68% of Enterprise discovery calls start with "how do you guarantee answers don't hallucinate?" or "walk me through your prompt injection defences." We are winning deals today specifically on the strength of our RAG faithfulness scores (91.3%), our NPS leadership in G2 Crowd, and the maturity of our Audit & Compliance Pack. Deepening those advantages over the next two years is the single most accretive use of R&D capital.

The cost of inaction is material. If we do not invest in agentic capabilities, our competitors (Microsoft Copilot for industry-specific workloads, Salesforce Einstein GPT in HR, and several well-funded start-ups in manufacturing AI) will commoditise the basic chat-RAG layer by FY2028, compressing our gross margins and making customer differentiation harder. The window to build a durable moat around domain RAG + agentic workflows + governance is 18-30 months. We intend to take it.

---

## 3. Pillar 1: Agentic Copilot Architecture

Today the DBiz GPT platform on our Open WebUI fork is primarily a retrieval-augmented chat system. A user asks a question, the system retrieves relevant chunks from the vector store, composes a grounded prompt, calls an LLM, and returns an answer. This architecture is already best-in-class for our verticals, but it is fundamentally a *reactive* system - it answers when asked, and rarely acts autonomously.

Under Pillar 1 we are evolving the platform into an **agentic copilot architecture** where the system proactively plans, reasons, uses tools, delegates to specialised sub-agents, and completes multi-step workflows on behalf of the user.

### 3.1 Core Agentic Design Principles

Five architectural principles govern all agentic work at DBizLabs:

1. **Human-in-the-loop default.** No agent may take an irreversible material action (e.g. modifying a live production Meiji OEE threshold, submitting a Bond trade order into a downstream OMS, or sending a candidate a Hirethm written offer) without explicit human acknowledgement of the planned action. Read-only actions and low-impact write actions may be fully automated after a customer-specific toggle is enabled.

2. **Planning loops: ReAct + Tree of Thoughts (ToT).** Complex multi-step tasks use a hybrid of ReAct (Reasoning + Acting interleaved) for breadth and a constrained Tree of Thoughts branch-and-prune for depth. Each node in the ToT tree has a token budget, a confidence threshold for pruning, and an observability span for post-hoc analysis.

3. **Budget guardrails as a first-class architectural concern.** Every agent invocation is subject to three independently enforceable budgets: (a) a token budget (input + output tokens), (b) a wall-clock execution time budget, and (c) a tool-call count budget. These budgets are enforced at the LangGraph orchestration layer before any LLM call, not just by the LLM gateway. The sensible-default 25k / 12k / 5-minute budget covers 94% of production agent tasks today; users can escalate to complex-task and executive-override budgets with proper approval.

4. **Tool use via MCP Servers, not ad-hoc integrations.** All agentic tools - from reading a Bond yield curve to writing a Jira ticket to querying a Meiji plant's SCADA historian - are exposed exclusively via Model Context Protocol (MCP) servers, not via bespoke Python functions hard-wired into the prompt. As of Q3 FY2026 we operate 11 production MCP servers (Jira, Gmail, Slack, Finance-ERP NetSuite, Meiji-MES, Hirethm-ATS, Bond-Pricing, Calendar v2, Google Drive v3, Notion, Internal Wiki/Confluence) with a total of 243 registered callable tools. Every tool implements parameter validation, least-privilege service account identity, and structured observability.

5. **Observability of every agent step.** Every step of every agent invocation - thought, tool call, tool result, LLM prompt, LLM completion, pruned branch, and budget checkpoint - is recorded as a structured span in LangSmith, mirrored to Sentry for error tracking, and aggregated in PostHog for product analytics. There is no "black box" agent in production. Customer success teams can pull a full trace of any agent task on request.

### 3.2 Agentic Copilot Version Roadmap

Pillar 1 KPI Target for FY2028: **40+ production agents** deployed across all three product lines, with a **tool-use success rate >= 90%** and Copilot DAU / MAU ratio >= 35%.

---

## 4. Pillar 2: Domain-Specific Hybrid RAG

Retrieval-Augmented Generation is the primary mechanism by which DBizLabs AI systems stay grounded in the specific, verifiable truth of each customer's documents and data. Our competitors treat RAG as a commodity layer: "pick a vector database, chunk documents, call embeddings, ship it." We do not. Over the last 18 months our internal benchmarking has shown repeatedly that careful, domain-aware engineering of every layer of the RAG stack - chunking, embeddings, vector search, keyword search, reranking, and evaluation - delivers compounding improvements in faithfulness, relevancy, and hallucination rates.

### 4.1 Hybrid Vector Store Architecture

**Primary vector store:** `pgvector` running on PostgreSQL 16 Aurora Serverless v2. This was selected after a four-month evaluation (Q1-Q4 2025) against Pinecone, Weaviate, Qdrant, pg_embedding, and Chroma-only deployments. pgvector delivers four strategic advantages:
- Strong consistency guarantees and transactional integrity, since vectors are stored in the same ACID relational database as tenant metadata. This eliminates the "stale chunk" problem that plagues separate vector DBs in multi-tenant SaaS environments.
- Deep operational familiarity across the engineering team. Our DBAs and platform engineers know PostgreSQL tuning, backup, and disaster recovery cold.
- Native support for IVFFlat indexes (deployed today for the ~200k chunk corpus at recall >= 99%) and HNSW indexes (on the roadmap for Q2 FY2027, once the Postgres 17 / pgvector 0.7 upgrade is stable at our scale).
- Fully compatible with our AWS RDS backup, point-in-time recovery, cross-region replication, and KMS encryption posture.

**Fallback / edge vector store:** Chroma open-source embedded vector store deployed at the edge in the EU and US regional clusters for low-latency queries, and in the on-prem Meiji MES appliance for air-gapped manufacturing deployments. Changes are asynchronously reconciled to pgvector with last-writer-wins + CRDT semantics.

**Hybrid retrieval strategy:** Every query is executed as a combination of BM25 keyword search (weight 0.35, configurable) and approximate nearest-neighbour semantic search on BGE-M3 embeddings (weight 0.65, configurable). Weights are tuned per-tenant based on a feedback loop from human-labelled relevant chunks.

### 4.2 Embeddings and Reranking Stack

**Embedding model: BAAI/bge-m3 (BGE Multilingual Mixture of Experts v3).** Deployed self-hosted on GPU instances to maintain data residency and avoid third-party data transfer. BGE-M3 was selected after a 6-week bake-off against OpenAI text-embedding-3-large, Cohere embed-multilingual-v3, Voyage Law-2, and local multilingual SentenceTransformer variants. BGE-M3 won on multilingual SG English + Tamil + Mandarin cross-lingual retrieval (+11.4% nDCG@10 on our multilingual golden set over the nearest competitor), fine-tunability on our domain corpus, and inference cost per 1M tokens of 58% lower than the commercial API alternatives.

**Reranker: ColBERT-IR v2 (late interaction, contextualised embeddings).** Currently in load testing; GA target Q4 FY2026. ColBERT was specifically chosen over Cohere rerank-3 for three reasons:
1. Superior multilingual performance on SG English + code-switched Tamil and Mandarin queries.
2. Transparent, interpretable token-level interaction scores (each rerank returns a per-token heatmap of query-document alignment, which we surface in the UI "source" tab to explain why a chunk was returned to Meiji quality engineers and Bond analysts).
3. Open-source, self-hostable, auditable weights - no third-party API dependency for a critical governance-sensitive layer.

### 4.3 Chunking Strategies Per Content Type

Chunking is one of the highest-leverage, most under-invested parts of the RAG stack in the industry. DBizLabs applies four different chunking strategies, selected automatically per document based on MIME type and metadata:

1. **Recursive character chunking (900 / 120 tokens, overlap):** The default. Applied to all general-purpose documentation, memos, HR policies, and chat transcripts. 900-token size was selected after an ablation study across 600 / 900 / 1200 / 1500 - 900 balanced context richness with retrieval precision. 120-token overlap preserves context across boundaries for mid-sentence and mid-paragraph breaks.

2. **Semantic boundary chunking (BGE-M3 similarity splits):** Used for long-form technical content such as Meiji MES standard operating procedures, Bond research notes, and Hirethm employee handbooks. Splits only at natural semantic boundaries (BGE cosine similarity < 0.62 between adjacent sentences). Improves context recall on procedure-heavy documents by 14.7% absolute in our QA harness.

3. **Hierarchical table-aware chunking (Unstructured.io + heuristic row-grouping):** Used exclusively for CSV, XLSX, and embedded tables in PDFs (Meiji OEE reports, Bond pricing tick tables, Hirethm compensation matrices). Preserves table-group semantics - no chunk ends mid-row-group, and header rows are repeated as context at the top of every table chunk.

4. **Per-message thread chunking (thread + 2-turn context window):** Used for Slack threads, Gmail conversations, and Support tickets. Preserves conversational turn structure.

### 4.4 RAG Evaluation: The DBiz Evaluation Harness

Trust is only as good as the evaluation. We maintain the **DBiz RAGQA Evaluation Harness** comprising:
- **2,400 golden question-and-answer pairs** (and growing at ~100 pairs/month), hand-labelled by domain SMEs in Meiji manufacturing, Bond capital markets, and Hirethm HR, across 12 document types.
- **12 category-specific adversarial QA suites**, including prompt-injection probes, out-of-domain trick questions, multi-hop reasoning questions, and edge-case multilingual queries.
- **Automated metrics computed per run**:
  1. Faithfulness (Ragas)
  2. Answer Relevancy (Ragas)
  3. Context Precision (Ragas)
  4. Context Recall (Ragas)
  5. Citation Groundedness (DBiz proprietary: % of answer sentences with >=1 valid supporting chunk)
  6. Hallucination Severity (human-rated on a 0-3 scale, quarterly calibration sample)
  7. Latency P50 / P95 for full RAG pipeline

Pillar 2 KPI Target for FY2028: **RAG faithfulness score >= 92%** on the full 12-document-type evaluation harness, sustained for 3 consecutive quarterly evaluations.

---

## 5. Pillar 3: Governance, Safety & Evaluations

The strongest technical RAG and agent stack in the world is worthless without customer trust that it is safe, fair, compliant, and auditable. Pillar 3 institutionalises that trust.

### 5.1 Regulatory Alignment

**Singapore AI Governance Act (A1 2026).** We completed our Phase 1 impact assessment (board-reviewed 11 September 2026). System tiering:
- **Tier 3 (High Risk, mandatory conformity assessment):** 3 systems - (i) Hirethm Candidate Shortlisting and Ranking, (ii) Meiji MES Predictive Quality AI release-to-customer decisions, and (iii) Bond Copilot pre-trade compliance check engine. These require pre-deployment conformity assessment by an MOH-appointed Conformity Assessment Body (CAB) before 1 February 2028.
- **Tier 2 (Moderate Risk, transparency and record-keeping):** 11 systems including Agentic Copilot general, Meiji OEE root cause, Bond yield curve scenario simulator.
- **Tier 1 (Low Risk, minimal obligations):** 10 consumer FAQ and general chat assistants.

**EU AI Act.** Our initial legal classification, reviewed with Bird & Bird LLP Brussels, classifies Hirethm ATS shortlisting and the Bond pre-trade compliance module as Annex III "High-Risk AI Systems" under the EU AI Act. Our EU-region clusters will be operated in full compliance, with the CE marking conformity assessment complete by no later than 1 Q 2028 (before the 36-month transitional deadline for existing high-risk systems). We do not currently develop or deploy any General-Purpose AI Model (GPAI / GPAI with systemic risk) - our deployments are all applied systems built on vendor-supplied LLMs.

### 5.2 Internal Governance Structures

**Responsible AI Council (RAIC).** Chaired by CTO Amala Appathurai with co-chair Head of Legal Santhana Krishnan. Membership: CPO, COO, Principal AI Safety Researcher, Data Scientist II (Fairness), one rotating Engineering Manager, one independent external advisor (appointed annually - Prof. Koh Hian Chye, SMU, to 31 July 2027). RAIC meets at minimum once every 14 days and has authority to:
- Block or roll-back any AI feature on safety or fairness grounds.
- Mandate additional evaluation or red-teaming prior to release.
- Approve any new Tier 2 or Tier 3 AI system classification.

**Red-Teaming and adversarial evaluation.** Quarterly red-team exercises conducted by an internal red-team of 6 engineers and 1 external security advisor with no access to the production model deployment. The Q3 2026 red-team uncovered 27 vulnerabilities (0 critical, 5 high, 22 medium), of which 18 are closed and 9 are on-track for closure by 31 October 2026. Annual external red-team by Mandiant (Google Cloud) for the Tier 3 Hirethm and Bond systems.

**Model Registry:** MLflow with a custom governance plugin, targeted GA Q4 2026. Every model (embedding, reranker, fine-tuned classifier, LLM gateway routing rules) is registered with: unique ID, version, training data lineage, owner, approval status, evaluation results, and deployment environment. No model is promoted to production without a signed-off RAIC model card.

**Prompt injection defence in depth.** Three complementary layers:
1. **Input-time heuristic + LLM classifier.** An onnx-runtime lightweight BERT-based classifier detects prompt-injection patterns at the API gateway before the main LLM is called.
2. **Delimiter + system prompt hardening.** All user-supplied content wrapped in XML tags with a corresponding system prompt instruction to ignore any instructions appearing inside the delimiters.
3. **Output-time canary + reflection check.** A secret canary token is embedded by the rewriter into each context chunk; if the token appears in the LLM output, the output is rejected as a potential prompt-injection leak and a human-in-the-loop review is triggered. Plus an LLM-based self-reflection check ("is this output derived exclusively from the instructions above the delimiter, or did it contain instructions from inside?").

**PII scrubbing and fairness:** All RAG context, LLM input prompts, and LLM outputs pass through a PII scrubber (Presidio + custom named-entity recognition model fine-tuned on Singapore / APAC personal data patterns) that redacts 18 classes of PII (NRIC, FIN, UEN, passport, phone, email, physical address, bank account, income, medical diagnosis, etc.) before any customer content reaches a third-party LLM provider.

Fairness metrics are tracked across four demographic variables on Hirethm candidate shortlisting outcomes: gender, age-band, ethnicity, and university-tier. Parity ratios are computed against the candidate pool distribution; any parity ratio below 0.80 or above 1.25 triggers an automatic investigation by the RAIC within 72 hours.

---

## 6. Security & Data Residency

DBizLabs operates a **three-region deployment architecture** to meet data residency, availability, and performance requirements:
- **SG Primary cluster:** ap-southeast-1 (AWS Singapore). All Singapore and APAC tenant data.
- **EU cluster:** eu-west-1 (Ireland). EEA / EU tenant data exclusively; data-at-rest never leaves the EU cluster.
- **US cluster:** us-east-1 (North Virginia). US, Canada, LATAM tenant data exclusively.

**Encryption:**
- **Data-at-rest:** AES-256-GCM applied at three layers: EBS volume encryption (AWS managed KMS key), PostgreSQL tablespace encryption (customer managed KMS key per region), and application-level encryption of Tier 3 fields (envelope encryption with DEK wrapped by a per-tenant key held in KMS HSM-backed).
- **Data-in-transit:** TLS 1.3 on all public endpoints (HSTS preload, TLS 1.0/1.1 disabled, modern cipher suites only). mTLS 1.3 on all internal service-to-service communications inside the VPC.

**Identity, Authentication, Authorisation:**
- **SSO:** SAML 2.0, OIDC 1.0, and Google Workspace social SSO for all products.
- **Identity Provider:** Keycloak 25.x deployed on Kubernetes, clustered across all three regions.
- **Provisioning:** SCIM 2.0 integration with Azure AD, Okta, and Google Workspace for automatic provisioning and de-provisioning of users.
- **Authorisation:** Dual RBAC + attribute-based access control (ABAC) engine. RBAC for role-granted privileges (admin, manager, user, viewer); ABAC for fine-grained rules such as "Bond analysts may only view the bond portfolios of clients on their coverage list." All authorisation decisions are logged to the audit trail for 7 years.

---

## 7. Engineering Operating Model

**Open-Source First.** The AI strategy cannot succeed without deep commitment to open-source software. Every layer of the platform is built on open-source components where commercially viable:
- **Client UI:** SvelteKit + Vite + Open WebUI fork (our mainline client). We contribute bug fixes and improvements upstream to Open WebUI on an ongoing basis (18 PRs merged upstream in FY2025 YTD).
- **LLM Gateway:** LiteLLM + custom self-hosted proxy (rate limiting, caching, quota enforcement, circuit-breaker fallback between providers).
- **Vector DB:** pgvector (PostgreSQL 16) + Chroma.
- **Agent Orchestration:** LangGraph + Open WebUI Agents SDK.
- **Rerank:** ColBERT-IR v2 (Stanford NLP open-source).
- **Chunking / Ingestion:** Unstructured.io, Playwright v1.60.
- **Eval Harness:** Ragas + custom RAGQA + LangSmith evaluation.

**Tech debt management.** A hard 20% engineering capacity allocation (equivalent to approximately 27 engineering FTEs at Q3 FY2026 headcount) is reserved each quarter for engineering health, debt pay-down, refactoring, and security work. The VP of Engineering reports tech debt inventory and the quarterly burn-down at the monthly Engineering Steering Committee (Architecture Review Board weekly; all-hands quarterly).

**Architecture Reviews and Platform Decisions:**
- Weekly Platform Architecture Review (PAR) for any proposed platform-level change affecting more than one system.
- Quarterly Architecture Summit where all domain architects, principal engineers, and CTO sign off on the roadmap for the following quarter.
- Architectural Decision Records (ADRs) mandatory for all decisions with system-wide impact; maintained in the monorepo.

**Observability, CI/CD, and Performance:**
- Product analytics: Sentry (error and performance monitoring) + PostHog (feature usage and funnel analytics).
- CI/CD: GitHub Actions for PR CI checks, Buildkite for deployment pipelines (blue/green on all three regions).
- Load testing: k6-based load tests executed before every GA release at a minimum of 5,000 concurrent simulated users, with P95 latency targets documented per endpoint.

---

## 8. KPIs & 2028 Targets (Balanced Scorecard)

| KPI Category              | KPI Name                                           | Baseline (Q3 FY2026)  | 2028 Target    | Measurement Frequency       |
|---------------------------|-----------------------------------------------------|------------------------|----------------|-----------------------------|
| Adoption & Usage          | Agentic Copilot DAU / MAU ratio                     | 18%                    | >=35%           | Monthly (PostHog)           |
| RAG Quality               | RAG Faithfulness (12-doc-type QA harness)           | 91.3%                  | >=92%           | Quarterly                   |
| Agent Reliability         | Tool-Use Success Rate (243 tools, all regions)      | 88.6%                  | >=90%           | Monthly (LangSmith)         |
| Deployment Density        | Agent deployments in production across 3 products   | 11                     | >=40            | Quarterly                   |
| Business Impact           | AI-attributed share of New ACV                      | 17%                    | >=30%           | Annually (Finance + RevOps) |
| Compliance & Cert - SOC2  | SOC 2 Type II Report                               | Kick-off 14 Oct        | Issued          | May 2027 target (one-time)  |
| Compliance & Cert - ISO   | ISO 27001 Certification                            | In scoping             | Issued          | Dec 2027 target (one-time)  |
| Compliance & Cert - Trust | SG AI Governance Trustmark                         | No submission          | Awarded         | Jun 2028 target (one-time)  |

---

## 9. Appendix A: Reference Architecture Table

| Layer               | Technology Stack                                                                    | Role in Architecture                                      | Owner Team          | Target GA / Status       |
|---------------------|-------------------------------------------------------------------------------------|-----------------------------------------------------------|---------------------|--------------------------|
| Client UI           | Open WebUI fork + SvelteKit + Vite                                                  | End-user chat, agent trace UI, settings, admin console    | UX & Client Platform| GA (Q1 FY2025)           |
| LLM Gateway         | LiteLLM + self-hosted proxy + Redis caching                                         | Multi-provider routing, rate limit, quota, caching, fallbacks | Platform Core  | GA (Q2 FY2025)           |
| LLM Providers       | OpenAI gpt-4o / gpt-4o-mini; Anthropic Claude 3.5 Sonnet; Google Gemini 1.5 Pro      | Inference models; routed by workload class                | Vendor Management   | GA (multi-vendor live)   |
| Vector Database     | pgvector on PostgreSQL 16 Aurora Primary; Chroma edge-store fallback                | Vector persistence, semantic + BM25 hybrid search          | Search Platform     | Primary: GA; HNSW upgrade: Q3 FY2026 |
| Embeddings          | BGE-M3 (BAAI/bge-m3) multilingual, self-hosted g5.xlarge                            | 2048-dim embeddings for retrieval; fine-tuned quarterly    | Search Platform     | GA                       |
| Reranker            | ColBERT-IR v2, self-hosted GPU                                                      | Late-interaction rerank of top-50 to top-5 retrieval      | Search Platform     | GA: Q4 FY2026            |
| Chunking            | Unstructured.io pre-proc + Recursive-character 900/120 + Semantic boundary + Table-aware | Document-to-chunk pipeline per content type            | RAG Team            | GA (Chunking v3.1 live)  |
| Web Loader          | Playwright v1.60; env PLAYWRIGHT_WS_URL=ws://playwright:3000; 8 SG + 4 EU + 4 US pods | JavaScript-aware crawling of HTML, SPAs, intranets         | Loader Team         | GA (rollout closed 23 Aug 2026) |
| Agent Orchestration | LangGraph + Open WebUI Agents SDK; ReAct + Tree-of-Thought planning module         | Agent state machine, budget guardrails, sub-agent handoff  | Agent Platform      | v1.0 GA, v2.0: Q1 FY2027 |
| Tool MCP Servers    | 11 MCP Servers: Jira, Gmail, Slack, Finance-ERP, Meiji-MES, Hirethm-ATS, Bond-Pricing, Calendar, Google Drive, Notion, Wiki | 243 registered callable tools for agent use    | MCP Platform        | 11 live; target 25 by FY2028 |
| Observability       | LangSmith (traces) + Sentry (errors + perf) + PostHog (product analytics)           | Full step-by-step agent tracing; error monitoring         | Platform Team       | GA (3 systems integrated) |
| Model Registry      | MLflow 2.x + Custom AI Governance Plugin (approval, fairness, lineage)              | Model lifecycle, cards, approval workflow before promotion | AI Governance Team  | GA: Q4 FY2026            |
| Evaluations         | Custom RAGQA harness (2400 QA pairs) + Ragas metrics + LangSmith eval harness       | 7-metric suite + adversarial red-team quarterly           | AI Governance Team  | GA (harness v3.2 live)   |
| Identity / IAM      | Keycloak 25.x + SCIM 2.0 + SAML 2.0 + OIDC 1.0; MFA enforced everywhere            | SSO, provisioning, RBAC + ABAC authorisation              | IAM & SecOps Team   | GA (Keycloak migrated Jun 2026) |

---

## 10. Appendix B: Glossary of Key Terms

**ABAC:** Attribute-Based Access Control - authorisation decisions based on attributes of the user, the resource, the action, and the environment (time, location, risk-level).

**ACV:** Annual Contract Value - the annualised recurring value of a customer contract.

**AURORA RDS:** AWS Aurora - managed relational database engine compatible with PostgreSQL, used as the primary DBizLabs OLTP + pgvector host.

**BGE-M3:** BAAI General Embedding - Multilingual Mixture of Experts v3; the multilingual open-source embedding model selected as the DBizLabs standard.

**BM25:** Best Matching 25 - the classical bag-of-words TF-IDF-style keyword retrieval ranking function used alongside ANN in the hybrid search layer.

**CHROMA:** Open-source embedded vector database used by DBizLabs at the edge and for on-prem Meiji appliances.

**COLBERT-IR v2:** Contextualized Late Interaction over BERT - a state-of-the-art late-interaction reranking model from Stanford NLP, open-sourced and self-hosted.

**DSO:** Days Sales Outstanding.

**EBITDA:** Earnings Before Interest, Taxes, Depreciation, and Amortisation.

**ELT:** Executive Leadership Team - CEO, CTO, CFO, COO, CPO.

**FY / FY2026:** Fiscal Year - DBizLabs fiscal year runs from 1 July to 30 June. FY2026 = 1 Jul 2025 to 30 Jun 2026.

**GA:** General Availability - the date a feature is released to all customers as a supported production capability.

**HNSW:** Hierarchical Navigable Small World - a state-of-the-art approximate nearest neighbour graph index.

**IVFFlat:** Inverted File Flat - approximate nearest neighbour index used in pgvector.

**KPI:** Key Performance Indicator.

**LANGGRAPH:** Open-source orchestration library from LangChain for building stateful, multi-step agent applications.

**LATENCY P95:** The 95th percentile end-to-end response time - the value slower than 95% of requests and faster than the slowest 5%.

**LITELMM:** Open-source library and proxy standardising API access across 100+ LLM providers.

**LLM:** Large Language Model.

**MCP:** Model Context Protocol - an open standard for exposing structured tools and data to LLMs, adopted as the DBizLabs exclusive tool-exposure mechanism.

**NRR:** Net Revenue Retention - a SaaS metric of expansion from existing accounts.

**OKTA / KEYCLOAK:** IAM products; Keycloak is the DBizLabs on-prem IDP; Okta and Azure AD are customer SSO identity providers federated via SAML.

**OPEN WEBUI / OWUI:** The open-source chat UI project forked and extended by DBizLabs as the primary client interface for DBiz GPT.

**PDPA:** Singapore Personal Data Protection Act 2012.

**PGVECTOR:** Open-source vector similarity search extension for PostgreSQL; the primary vector store for DBizLabs hybrid RAG.

**PLAYWRIGHT:** Microsoft open-source library for browser automation, used as the primary web-loader rendering engine.

**RAG:** Retrieval-Augmented Generation - the pattern of retrieving relevant context from a knowledge store, injecting that context into an LLM prompt, and grounding the generated answer in the retrieved evidence.

**RAGAS:** Open-source evaluation framework for RAG quality metrics.

**RERANK:** The process of taking a larger set of initial retrieval candidates (e.g. top 50) and re-ordering them with a stronger, slower model to surface the top 5-10 most relevant to the query.

**ReAct:** Reasoning + Acting - a prompting paradigm where the LLM alternates between reasoning about what to do next and using a tool.

**SCIM:** System for Cross-domain Identity Management - the standard protocol for automated user provisioning and deprovisioning.

**SOC 2 TYPE II:** Service Organisation Control 2 Type II - the AICPA audit standard for security, availability, processing integrity, confidentiality, and privacy controls.

**ToT / TREE of THOUGHTS:** A prompting paradigm where multiple candidate reasoning chains are generated, evaluated, and pruned to find the best solution path.

**YIELD CURVE:** In Bond Copilot context - the relationship between bond yields (interest rates) and different maturities, used for valuation and scenario simulation.

---

*End of Whitepaper. Next scheduled revision: 1 June 2027, or earlier in the event of material changes to the regulatory landscape or strategic direction.*

**Distribution List (controlled):** All Board of Directors; ELT; VP Engineering, VP Product, VP Sales, VP CSM, VP People; Principal Engineers and above; AI Governance Council members.

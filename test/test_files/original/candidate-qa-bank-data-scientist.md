# DBizLabs Senior Data Scientist Interview Q&A Bank

## 1. SQL & Data Manipulation

### Q1. Write SQL to find the top 5 customers by ACV from a `meiji_contracts` table with columns `(customer_id, customer_name, acv_sgd, start_date, end_date, status)`.

**Answer:**  
I would first filter to active contracts, aggregate ACV by customer, then order descending and limit to five rows.

```sql
SELECT
  customer_id,
  customer_name,
  SUM(acv_sgd) AS total_acv_sgd
FROM meiji_contracts
WHERE status = 'active'
  AND CURRENT_DATE BETWEEN start_date AND end_date
GROUP BY customer_id, customer_name
ORDER BY total_acv_sgd DESC
LIMIT 5;
```

At DBizLabs, I would also validate whether ACV should be normalized for co-termed contracts and whether implementation revenue should be excluded so Finance and Sales use the same definition.

### Q2. How would you do 3-sigma outlier detection on Meiji OEE hourly readings?

**Answer:**  
I would calculate the plant-line mean and standard deviation over a defined baseline window, then flag rows where `ABS(oee - mean) > 3 * stddev`. For manufacturing data, I would segment by line, shift, and product family because mixing different operating regimes can produce false positives. I would also compare 3-sigma against robust methods like IQR or median absolute deviation because OEE distributions are often skewed after maintenance events.

### Q3. Use window functions to compute a running 7-day average DSO per sales rep.

**Answer:**  
I would aggregate invoice-level DSO to a daily rep grain first, then use a window frame covering the previous six days and current day.

```sql
WITH rep_day AS (
  SELECT
    sales_rep_id,
    invoice_date::date AS d,
    AVG(dso_days) AS avg_dso_day
  FROM ar_invoice_metrics
  GROUP BY sales_rep_id, invoice_date::date
)
SELECT
  sales_rep_id,
  d,
  AVG(avg_dso_day) OVER (
    PARTITION BY sales_rep_id
    ORDER BY d
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS running_7d_avg_dso
FROM rep_day;
```

For DBizLabs, I would join this with collections actions to see whether DSO changes came from rep behavior, customer mix, or invoice disputes.

### Q4. How would you optimize a Bond pricing historical tick table with 1 billion rows?

**Answer:**  
I would partition by trading date first, then subpartition or cluster by instrument or venue depending on query shape. The table should have compressed cold partitions, covering indexes for the most common filters, and summary tables for minute or hour bars so analysts do not repeatedly scan raw ticks. If the platform supports it, I would also separate hot intraday data from historical archive storage and benchmark both partition pruning and join performance against risk analytics workloads.

### Q5. What join strategy would you use across Hirethm tables `candidate`, `application`, `interview`, and `offer`?

**Answer:**  
I would define the analytical grain before joining, because the wrong grain can duplicate rows and distort conversion metrics. For funnel analysis, I would start from `application` as the spine, left join interview and offer summaries, and aggregate interview rows beforehand if there can be multiple panels per application. I would also keep source timestamps so we can calculate stage aging, drop-off, and fairness metrics by protected cohorts without accidental leakage.

## 2. ML Fundamentals

### Q6. Explain L1 vs L2 regularization in a salary prediction model.

**Answer:**  
L1 tends to drive some coefficients exactly to zero, which is useful when we want sparsity and a simpler explanation of compensation drivers. L2 shrinks coefficients smoothly and is often more stable when many correlated features exist, such as location, grade, manager band, and business unit. In a DBizLabs salary model, I would usually start with elastic net so we get both shrinkage and feature selection while preserving interpretability for People Ops.

### Q7. Why are precision, recall, and F1 more important than accuracy for Hirethm candidate shortlisting?

**Answer:**  
Accuracy can look high even when the model misses strong candidates, especially if the positive class is small. Recall matters because false negatives mean losing qualified applicants, while precision matters because false positives create recruiter workload and damage trust in the scoring tool. At DBizLabs, I would also evaluate subgroup recall and calibration by gender, school tier, and career-switcher status so performance does not hide bias.

### Q8. Gradient boosting vs random forest for Meiji yield prediction?

**Answer:**  
Gradient boosting usually wins when the data has structured nonlinear interactions and we need strong predictive power on tabular features such as machine settings, batch conditions, operator shifts, and defect histories. Random forest is more robust out of the box and can be easier to train quickly, but it often lags on fine-grained optimization problems. For Meiji yield prediction, I would benchmark both, then inspect stability across plants and drift across new product introductions before choosing a production model.

### Q9. You have a 20:1 imbalanced churn dataset. What three strategies would you try?

**Answer:**  
First, I would adjust the loss with class weights so the model does not ignore the minority churn class. Second, I would test resampling strategies such as SMOTE or balanced minibatches, while being careful not to distort time ordering. Third, I would optimize the decision threshold against business cost, because in Bond Copilot it may be cheaper to over-flag a few at-risk accounts than to miss a genuine churn signal.

### Q10. How would you test three Bond Copilot UI variants with sequential testing?

**Answer:**  
I would predefine the primary metric, stopping rules, and guardrail metrics before launch, then use a sequential framework such as group sequential testing or a Bayesian monitoring approach to avoid inflated false positives from peeking. The analysis would stratify by account tier because enterprise bond traders and smaller wealth teams behave differently. I would also log exposure consistency carefully so switching devices or sessions does not contaminate treatment assignment.

## 3. LLM / RAG

### Q11. What chunking strategy would you use for mixed Meiji MES docs across PDF, DOCX, CSV, and TXT?

**Answer:**  
I would use at least three strategies. For narrative PDFs and DOCX files, recursive character chunking around 900 characters with 120 overlap works well as a baseline. For tabular CSV content, I would preserve headers and chunk by logical row groups so numerical context stays intact. For policy or SOP TXT files, I would prefer section-aware chunking using headings and bullets because semantically complete policy sections retrieve better than arbitrary windows.

### Q12. Name four ways to mitigate RAG hallucinations.

**Answer:**  
First, rerank retrieved passages so the final context is both relevant and high precision. Second, force citation-grounded generation so the assistant must answer from retrieved evidence and return source references. Third, use self-consistency or answer verification to compare multiple draft responses against the same evidence. Fourth, maintain an evaluation harness with adversarial queries so regressions show up before release rather than after users in DBiz GPT notice them.

### Q13. Why choose `pgvector` with IVFFlat at around 200k chunks? When would you consider HNSW?

**Answer:**  
At 200k chunks, `pgvector` keeps the system operationally simple because search lives close to the application database, permissions, and metadata joins. IVFFlat is often sufficient at that scale when recall is boosted with hybrid lexical retrieval and reranking. I would consider HNSW if latency or recall became a bottleneck under heavier concurrent search loads, but I would still weigh that against operational complexity and the team's comfort with Postgres-centered tooling.

### Q14. ColBERT reranker vs Cohere rerank for Singapore English plus Tamil and Mandarin queries?

**Answer:**  
ColBERT gives more control, can be tuned in-house, and may be attractive when we want tighter governance over ranking behavior and cost. Cohere rerank is faster to adopt and can perform very well, but it adds vendor dependency and sometimes less transparency into failure modes. For DBizLabs, I would benchmark both on multilingual query sets from Meiji support tickets, Bond research notes, and Hirethm recruiter queries before locking in a production choice.

### Q15. What seven metrics would you track in a RAG evaluation pipeline, and how would you build the golden set?

**Answer:**  
I would track retrieval recall, precision at k, context relevance, answer faithfulness, answer completeness, citation correctness, and latency. The golden set should be built from real product workflows: manufacturing exception analysis for Meiji, bond risk and pricing questions for Bond Copilot, and recruiting workflow questions for Hirethm. I would source examples from support tickets, internal SMEs, and board-approved policy documents, then require human-reviewed answer rubrics for at least a few hundred prompts before automating the rest.

### Q16. How would you build a prompt injection detector for the Open WebUI chat endpoint?

**Answer:**  
I would combine three layers. The first is lightweight rule and pattern detection for phrases that try to override system instructions or exfiltrate secrets. The second is a classifier model trained on benign versus injected prompts, including multilingual variants. The third is a policy engine that checks requested tool calls and data access against user permissions, because even a good detector should not be the last line of defense.

## 4. Business & Product

### Q17. Bond Copilot churn is 5% and needs to get to 2%. What are three data-driven levers?

**Answer:**  
First, build a renewal risk model that identifies low-usage and low-adoption accounts early enough for Customer Success to intervene. Second, segment product usage by persona so we can see whether traders, compliance officers, or portfolio managers are failing to realize value. Third, quantify which workflows correlate with renewal, then push onboarding and feature nudges toward those high-retention behaviors.

### Q18. Meiji MES OEE drops from 78% to 62% after an upgrade. Walk through five root-cause steps.

**Answer:**  
I would first validate the telemetry to rule out instrumentation or mapping errors introduced by the release. Second, segment the drop by plant, line, shift, and product family to localize impact. Third, compare pre- and post-release event logs, alarms, and deployment timestamps. Fourth, review process changes with plant engineering to understand whether the issue is software, training, or operating practice. Fifth, run a rollback or controlled feature flag test if needed to isolate the exact change.

### Q19. Propose a Q4 FY2026 OKR for the data science team.

**Answer:**  
One strong objective would be: "Increase trusted AI adoption across DBizLabs products." Key results could include lifting RAG faithfulness in DBiz GPT from 91.3% to 93.0%, reducing Bond Copilot churn model false negatives by 20%, and shipping a Meiji anomaly model that cuts mean time to root cause by 15%. I would also add one platform KR around reusable evaluation tooling so each product team benefits from shared infrastructure.

## 5. Coding & Architecture

### Q20. Design a distributed batch plus stream inference pipeline for 1 million nightly re-chunks.

**Answer:**  
I would separate ingestion, parsing, chunking, embedding, and indexing into independent stages connected by durable queues. Nightly batch jobs would handle full refresh and backfill, while a stream path would process newly uploaded or modified documents with low latency. I would store lineage metadata for each chunk version so we can compare retrieval quality across chunking algorithms and roll back if a new strategy hurts Meiji, Bond, or Hirethm search quality.

### Q21. Write a Python class to compute faithfulness across 2,000 prompts. What matters most?

**Answer:**  
The class should separate data loading, model inference, citation extraction, evidence matching, and metric aggregation so each part can be tested independently. It should also support retries, parallel execution, and deterministic output logging because evaluation code tends to be harder to trust than model code. At DBizLabs, I would expose both aggregate scores and per-domain slices so we know whether one product line is hiding weaknesses in another.

### Q22. How would you design an MCP server to connect a Meiji SCADA historian to Open WebUI agents?

**Answer:**  
I would keep the MCP server narrow and explicit: read-only operational queries first, with strongly typed tools for historian reads, asset metadata, and alarm summaries. Each tool should enforce row, time-range, and plant scope permissions so an agent cannot overreach even if prompted badly. I would also log every tool call with user, plant, asset, and purpose metadata because auditability is mandatory when agents touch manufacturing data.

## 6. Behavioural

### Q23. Tell me about a time your model harmed a downstream decision.

**Answer:**  
I would expect a strong candidate to admit the failure clearly, explain the mechanism, and show how they repaired both model and process. In the DBizLabs context, a good answer might involve a Hirethm score over-weighting brand-name employers and reducing progression rates for capable nontraditional candidates. The best response includes rollback, stakeholder communication, fairness review, and permanent monitoring changes rather than just tuning a threshold.

### Q24. How do you disagree with a PM about data interpretation?

**Answer:**  
I start by aligning on the business question and decision that depends on the data, because many disagreements are really disagreements about framing. Then I walk through assumptions, definitions, and sensitivity analyses rather than trying to "win" the argument. At DBizLabs, I would especially want to show how alternate cuts of Meiji plant data or Bond usage cohorts can produce different stories, and how to decide which story matches the product decision.

### Q25. Tell me about a project you scrapped and why.

**Answer:**  
The strongest answers show judgment, not sunk-cost attachment. For example, a candidate might describe stopping a complex deep learning initiative for Bond price movement prediction after finding that simpler market microstructure features plus gradient boosting performed just as well in production and were easier to explain to clients and Risk. I would look for evidence that they preserved useful lessons, documented the decision, and redirected the team toward higher-value work.

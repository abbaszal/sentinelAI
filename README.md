# remember

For duplicated payment:

at least 2 successful payments + 

successful payment total > order total 

=

duplicate-payment condition

For refund policy:

processing + no shipment
→ True

shipped
→ False

delivered
→ False

cancelled
→ False

processing + shipment exists
→ False



# remember as first result:

''

python -m sentinel.evaluation.retrieval_eval 

''

======================================================================
SentinelAI Retrieval Evaluation
======================================================================

Cases:    22
Recall@1: 0.636
Recall@3: 0.818
Recall@5: 0.955
MRR:      0.759

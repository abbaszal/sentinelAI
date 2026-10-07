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

python -m sentinel.evaluation.compare_retrievers

''

TF-IDF
--------------------------------------------------
Recall@1: 0.636
Recall@3: 0.818
Recall@5: 0.955
MRR:      0.759


Embeddings + FAISS
--------------------------------------------------
Recall@1: 0.864
Recall@3: 1.000
Recall@5: 1.000
MRR:      0.932

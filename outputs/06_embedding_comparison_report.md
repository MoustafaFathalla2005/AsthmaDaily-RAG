# Embedding Model Comparison Report

Evaluated on C:\Users\ADAM-LAP\Downloads\asthmadaily_rag (1)\asthmadaily_rag\eval\Day2_Evaluation_Test_Set.csv (k=3, chunk_size=400 tok, overlap=50 tok).

| Model | Type | Precision@3 | Hit Rate@3 | MRR | Build (s) | Eval (s) |
|---|---|---|---|---|---|---|
| minilm-l6-v2 | huggingface | 0.033 | 0.100 | 0.050 | 49.24 | 0.18 |
| bge-small-en | huggingface | 0.033 | 0.100 | 0.033 | 173.82 | 0.3 |
| gte-small | huggingface | 0.033 | 0.100 | 0.100 | 1342.57 | 0.77 |
| tfidf-svd | tfidf_svd | 0.000 | 0.000 | 0.000 | 6.44 | 0.33 |

**Best on this run: `minilm-l6-v2`** (Precision@3 = 0.033).

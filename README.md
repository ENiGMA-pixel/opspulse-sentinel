# opspulse-sentinel

**Note on Data:** To run the full pipeline from scratch, download `HDFS_2k.log` from the LogHub dataset and place it in the `data/raw/` directory.

OpsPulse Sentinel is an enterprise AI agent designed to slash diagnostic MTTR from 90 minutes to under 60 seconds. It uses Gemini 3.1 Pro/Flash for semantic reasoning across telemetry, deployment logs, and system manifests. Integrated with ChromaDB for historical RAG and Streamlit for its UI, it provides automated, human-gated root cause analysis.

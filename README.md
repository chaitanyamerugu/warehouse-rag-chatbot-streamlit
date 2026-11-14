# Warehouse Management AI Chatbot

A Generative AI chatbot that uses Retrieval-Augmented Generation (RAG) to help warehouse supervisors find orders at risk of missing their carrier cutoff, understand why, and decide what to do.

## How it works
1. **Prediction:** an XGBoost model scores each order's delay probability at release time, and SHAP identifies the top drivers behind each score.
2. **Retrieval:** for each question, a TF-IDF retriever pulls the most relevant passages from the knowledge base (solution overview, operations playbook, data dictionary, analytics summary) and the scored order records. Orders named by ID, such as SO-92802, are looked up directly.
3. **Generation:** Claude writes the answer using only the retrieved passages and cites them.

## Files
- `streamlit_app.py`: Streamlit app (chat, risk dashboard, about tab)
- `rag.py`: retrieval layer (TF-IDF indexes, order lookup, prompt rules)
- `knowledge/`: documents the retriever searches
- `data/scored_orders.csv`: 7,073 test-period orders (April to June 2026) with delay probability, risk drivers, and suggested action

## Configuration
Set these in Streamlit Community Cloud under **App settings > Secrets**:
```toml
ANTHROPIC_API_KEY = "your-key"
# optional
CLAUDE_MODEL = "claude-sonnet-5-5"
```

## Run locally
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

All data is synthetic and created for a graduate course project.

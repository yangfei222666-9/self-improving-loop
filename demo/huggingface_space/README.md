# Hugging Face Space Demo

Use this folder as the source for a public Hugging Face Space.

Recommended Space settings:

- SDK: `Streamlit`
- Visibility: `Public`
- App file: `app.py`

Local smoke run:

```bash
python3 -m pip install streamlit
python3 -m streamlit run demo/huggingface_space/app.py
```

The app is deterministic and does not call external LLM providers. It records
success/failure traces under `.demo-traces/`, which is ignored by git.

# Elements Report
Generated: 2025-11-17T17:33:44.299896Z
Graph: Insight Report (3 nodes)
Tags: report

## Outputs
{
  "status": "queued",
  "notebook": "elements_reporting.ipynb",
  "parameters": {
    "format": "markdown",
    "inputs": {
      "parameters": "[gpt-4o-mini | temp=0.2] Summarize the latest lab findings"
    }
  }
}

## Trace
- node_report_prompt (prompt): inputs={} -> outputs={'text': 'Summarize the latest lab findings', 'variant': 'raw'}
- node_report_llm (llm): inputs={'prompt': 'Summarize the latest lab findings'} -> outputs={'response': '[gpt-4o-mini | temp=0.2] Summarize the latest lab findings', 'model': 'gpt-4o-mini', 'temperature': 0.2}
- node_report_notebook (notebook): inputs={'parameters': '[gpt-4o-mini | temp=0.2] Summarize the latest lab findings'} -> outputs={'status': 'queued', 'notebook': 'elements_reporting.ipynb', 'parameters': {'format': 'markdown', 'inputs': {'parameters': '[gpt-4o-mini | temp=0.2] Summarize the latest lab findings'}}}
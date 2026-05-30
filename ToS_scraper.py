import json
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI(api_key="your_key")

# Load your data
with open('ai_act_risks.json', 'r') as f:
    risks_data = json.load(f)

with open('platform_tos.json', 'r') as f:
    tos_data = json.load(f)

# Clean ToS Text
clean_tos = BeautifulSoup(tos_data["text"], "html.parser").get_text(separator="\n")

results = []

# Process only 'risk' entries
for entry in risks_data["entries"]:
    if entry["category"] == "risk":
        print(f"Analyzing: {entry['tag']}...")
        
        prompt = f"""
        ACT AS: EU AI Act Compliance Auditor.
        
        RISK TO DETECT: {entry['type']} ({entry['tag']})
        LEGAL DEFINITION: {entry['definition']}
        
        TERMS OF SERVICE TEXT:
        {clean_tos}
        
        TASK:
        1. Determine if the ToS contains clauses that describe, allow, or relate to this specific risk.
        2. If 'detected' is true, provide the exact quote.
        3. Provide a brief legal reasoning.

        RETURN ONLY JSON:
        {{
            "tag": "{entry['tag']}",
            "detected": boolean,
            "evidence_text": "string or null",
            "reasoning": "string"
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o", # Recommended for complex EU law reasoning
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        
        results.append(json.loads(response.choices[0].message.content))

# Save the final report
with open('risk_detection_report.json', 'w') as f:
    json.dump(results, f, indent=4)
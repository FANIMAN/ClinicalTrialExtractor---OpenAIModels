import re
import requests
import csv
import json
from xml.etree import ElementTree as ET

# PubMed Search API Parameters
pubmed_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
pubmed_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# OpenRouter LLM API
llm_api_url = "https://openrouter.ai/api/v1/chat/completions"
llm_api_key = (
    "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"
)

# Example search keyword
keyword = input("Enter the clinical trial keyword (e.g., Breast Cancer): ")

# Pagination control
total_pages = int(input("Enter the number of pages to scrape: "))


# Check available models and allow model selection
def check_available_models():
    models_url = "https://openrouter.ai/api/v1/models"
    response = requests.get(models_url)
    if response.status_code == 200:
        models = response.json()
        with open("available_models.json", "w") as json_file:
            json.dump(models, json_file, indent=4)
        print("Models have been exported to 'available_models.json'")
        return models
    else:
        print(f"Failed to fetch available models: {response.status_code}, {response.text}")
        return None


# Choose a model from available options
def choose_model(models):
    model_list = models.get("data", [])
    for idx, model in enumerate(model_list):
        print(f"{idx + 1}. {model['id']}")
    choice = int(input("Select a model by number: "))
    return model_list[choice - 1]["id"] if 0 < choice <= len(model_list) else None


# Fetch PubMed results
def fetch_pubmed_results(keyword, page_num):
    params = {
        "db": "pubmed",
        "term": f'{keyword} AND "Randomized Controlled Trial"[pt]',
        "retstart": page_num * 10,
        "retmax": 10,
        "usehistory": "y",
    }
    response = requests.get(pubmed_search_url, params=params)
    response.raise_for_status()  # Raise an error for HTTP errors
    return response.text


# Function to parse trial IDs from the XML response
def parse_trial_ids(xml_response):
    root = ET.fromstring(xml_response)
    return [id_elem.text for id_elem in root.findall(".//Id")]


# Fetch specific trial information (with retries for resilience)
def fetch_trial_info(trial_id, retries=3):
    params = {"db": "pubmed", "id": trial_id, "rettype": "abstract", "retmode": "text"}
    for attempt in range(retries):
        response = requests.get(pubmed_fetch_url, params=params)
        if response.status_code == 200:
            return response.text
        elif attempt < retries - 1:
            print(f"Retry {attempt + 1}/{retries} for trial {trial_id}")
        else:
            print(f"Failed to fetch trial {trial_id} after {retries} attempts")
            return None


# Call LLM API for structured data using OpenRouter (POST request)
def call_llm_api(text_data, selected_model):
    headers = {
        "Authorization": f"Bearer {llm_api_key}",
        "Content-Type": "application/json",
    }

    # Including text_data in the message content
    payload = {
        "model": selected_model,
        "messages": [
            {
                "role": "user",
                "content": f"""
I am giving you text that is intended to have clinical trial results data. 
Here is the clinical trial data: 
{text_data}

Depending on the above clinical trial data provided, please answer the following questions and structure the response as outlined below:

Trial Identification:
1. How many Clinical Trials are there?
1A. [Answer]
Trial1-Info:NCT#:TrialName:#ofPatients
...

Trial Questions:
1. What is the NCT# Associated with this clinical trial?
1A. [Answer]
2. What Phase is the clinical trial in? Phase 1, Phase 2, Phase 3, or Phase 4?
2A. [Answer]
3. What type of cancer(s) was this trial studying? ie- NSCLC, SCLC, Melanoma, Leukemia, Colon etc
3A. [Answer]
4. Describe the Cancer Type?
4A. [Answer]
5. Who sponsored the clinical trial?
5A. [Answer]
6. What were the novel findings of this trial?
6A. [Answer]
7. What conclusions were reached regarding this clinical trial?
7A. [Answer]
8. Is there any other relevant information that might make this clinical trial unique?
8A. [Answer]
9. Were there any subgroups in this study that the clinical trial identified had heightened responses to the intervention?
9A. [Answer]

Study Groups:
Group1:ControlGroup:DrugNames(s):UniqueCharacteristics
10. What are the study groups?
10A. Study Groups - [Answer]
...

Group Questions:
Group#-1.[Question Restated]
Group#-1A.[Answer]
Group#-2.[Question Restated]
Group#-2A.[Answer]
...
""",
            }
        ],
    }

    # Print the entire payload to debug the message being sent
    print("\n\n\n\n\n")  # Five blank lines
    print("Payload being sent to LLM API:")
    print(json.dumps(payload, indent=4))  # Pretty-print the payload for better readability

    try:
        response = requests.post(llm_api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raises HTTPError for bad responses
        structured_data = response.json()
        print("\n\n\n\n\n")  # Five blank lines
        print(f"Response data from the API: {structured_data}")  # Print the error response for more context

        # Extract content from the response
        print("\n\n\n\n\n")  # Five blank lines
        content = structured_data['choices'][0]['message']['content']
        print(f"Content from inside response: {content}")  # Print the error response for more context


        # Function to safely extract data using regex
        def safe_search(pattern, string):
            match = re.search(pattern, string)
            if match:
                return match.group(1)
            return "Not specified"  # Default value if not found

        # Regular expressions to find required data
        nct_number = safe_search(r"1A\.\s*(.+)", content)  # Extracting value of '1A'
        phase = safe_search(r"2A\.\s*(.+)", content)  # Extracting value of '2A'
        cancer_type = safe_search(r"4A\.\s*(.+)", content)  # Extracting value of '3A'
        sponsor = safe_search(r"5A\.\s*(.+)", content)  # Extracting value of '5A'
        findings = safe_search(r"6A\.\s*(.+)", content)  # Extracting value of '6A'
        conclusions = safe_search(r"7A\.\s*(.+)", content)  # Extracting value of '7A'

        # Example of how to print the extracted values
        print(f"NCT Number: {nct_number}")
        print(f"Phase: {phase}")
        print(f"Cancer Type: {cancer_type}")
        print(f"Sponsor: {sponsor}")
        print(f"Findings: {findings}")
        print(f"Conclusions: {conclusions}")

        study_groups = safe_search(r"10A.\.\s*(.+)", content)
        group_info = safe_search(r"Group1-1A.\.\s*(.+)", content)
        orr = "Not specified"  # Placeholder; define extraction logic if available
        pfs = "Not specified"  # Placeholder; define extraction logic if available
        os = "Not specified"   # Placeholder; define extraction logic if available

        # Map structured data to the required CSV format
        return {
            "Trial Identification": f"Trial1-Info:{structured_data.get('id')}",
            "NCT#": nct_number,
            "Phase": phase,
            "Cancer Type": cancer_type,
            "Sponsor": sponsor,
            "Findings": findings,
            "Conclusions": conclusions,
            "Study Groups" : study_groups,
            "Group Info": group_info,
            "ORR": orr,
            "PFS": pfs,
            "OS": os,
        }
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        print(f"Response content: {response.text}")  # Print the error response for more context
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None



# Save extracted data to CSV
def save_to_csv(trial_data, filename="clinical_trials.csv"):
    if trial_data:
        fieldnames = [
            "Trial Identification",
            "NCT#",
            "Phase",
            "Cancer Type",
            "Sponsor",
            "Findings",
            "Conclusions",
            "Study Groups",
            "Group Info",
            "ORR",
            "PFS",
            "OS",
        ]
        with open(filename, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trial_data)
        print(f"\nData has been saved to {filename}")
    else:
        print("No trial data to save.")


# Main script execution
if __name__ == "__main__":
    models = check_available_models()  # Check available models first
    if models:
        selected_model = choose_model(models)  # Let user select a model
        all_trials = []
        for page in range(total_pages):
            xml_data = fetch_pubmed_results(keyword, page)
            if xml_data:
                # Parse trial IDs
                trial_ids = parse_trial_ids(xml_data)
                print(f"Parsed trial IDs for page {page + 1}: {trial_ids}")
                for trial_id in trial_ids:
                    trial_info = fetch_trial_info(trial_id)
                    if trial_info:
                        print(f"\nFetched trial info for ID {trial_id}:")
                        print(trial_info)
                        structured_data = call_llm_api(trial_info, selected_model)
                        if structured_data:
                            print(f"Structured data for trial ID {trial_id}: {structured_data}")
                            all_trials.append(structured_data)

        # Save to CSV
        save_to_csv(all_trials)
    else:
        print("No models available, cannot proceed.")

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

# Fetch specific trial information (with retries for resilience)
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

Trial Questions:
1. What is the NCT# Associated with this clinical trial?
11A. [Answer]
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

Group Questions:
Group1-1. Is this the control group or the intervention group?
Group1-1A. [Answer]
Group1-2. What drug(s) was the clinical trial studying in this group/cohort?
Group1-2A. [Answer]
Group1-3. What was the Treatment ORR in this group/cohort?
Group1-3A. [Answer]
Group1-4. What was the Intervention Treatment PFS in this group/cohort?
Group1-4A. [Answer]
Group1-5. What was the Intervention Treatment OS in this group/cohort?
Group1-5A. [Answer]
Group1-6. What percentage of patients in the intervention group discontinued?
Group1-6A. [Answer]
Group1-7. Did the group specifically meet its endpoints? Yes or No or NA
Group1-7A. [Answer]
Group1-8. Did the group include patients who had specific stages of cancer? If so, what stages?
Group1-8A. [Answer]
Group1-9. Did the group include patients who had targets? (such as mutations, biomarkers, genes, etc.)?
Group1-9A. [Answer]
Group1-10. Did the group include patients who had previously taken a specific drug type?
Group1-10A. [Answer]
Group1-11. Did the group include patients who had specifically developed resistance to specific drugs? If so, list the drugs.
Group1-11A. [Answer]
Group1-12. Did the group include patients who had specifically developed resistance to specific drug types? If so, list the drug types.
Group1-12A. [Answer]
Group1-13. Did the group include patients who had brain metastases? Yes or No
Group1-13A. [Answer]
Group1-14. Did the group include patients who had previous surgery? Yes or No
Group1-14A. [Answer]
Group1-15. Did the group include patients who had “advanced” cancer? Yes or No
Group1-15A. [Answer]
Group1-16. Did the group include patients who had “metastatic” cancer? Yes or No
Group1-16A. [Answer]
Group1-17. Did the group include patients who were previously untreated?
Group1-17A. [Answer]
Group1-18. Did the group include patients who had previously taken a specific drug? If so, list the drugs.
Group1-18A. [Answer]
Group1-19. Did the group include patients who had NOT previously taken a specific drug? If so, list the drugs.
Group1-19A. [Answer]
Group1-20. Did the group include patients who were receiving 1st, 2nd, 3rd, 4th, 5th, etc. therapy? Please specify.
Group1-20A. [Answer]
Group1-21. Was the treatment for this group well tolerated?
Group1-21A. [Answer]
Group1-22. Were there specific adverse reactions associated with this group?
Group1-22A. [Answer]
Group1-23. Has the intervention drug(s) for this group been approved? Yes, No, or NA
Group1-23A. [Answer]
Group1-24. What other efficacy data points were measured? (ie- TTP, DoR, CR, PR, SD, CBR, pCR, etc.)? Give in the format TTP:X, DoR:X, CR:X.
Group1-24A. [Answer]
"""
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
        content = structured_data['choices'][0]['message']['content']
        print(f"Content from inside response: {content}")  # Print the error response for more context

        # Function to safely extract data using regex
        def safe_search(pattern, string):
            match = re.search(pattern, string)
            if match:
                return match.group(1)
            return "Not specified"  # Default value if not found

        # Regular expressions to find required data
        # nct_number = safe_search(r"1A\.\s*(.+)", content)
        nct_numberr = safe_search(r"11A\.\s*(.+)", content)
        phase = safe_search(r"2A\.\s*(.+)", content)
        cancer_type = safe_search(r"4A\.\s*(.+)", content)
        sponsor = safe_search(r"5A\.\s*(.+)", content)
        findings = safe_search(r"6A\.\s*(.+)", content)
        conclusions = safe_search(r"7A\.\s*(.+)", content)

        # Group questions extraction
        study_groups = safe_search(r"10A\.\s*(.+)", content)
        group_info = safe_search(r"Group1-1A\.\s*(.+)", content)
        groupX1 = safe_search(r"Group1-1A\.\s*(.+)", content)
        groupX2 = safe_search(r"Group1-2A\.\s*(.+)", content)
        groupX3 = safe_search(r"Group1-3A\.\s*(.+)", content)
        groupX4 = safe_search(r"Group1-4A\.\s*(.+)", content)
        groupX5 = safe_search(r"Group1-5A\.\s*(.+)", content)
        groupX6 = safe_search(r"Group1-6A\.\s*(.+)", content)
        groupX7 = safe_search(r"Group1-7A\.\s*(.+)", content)
        groupX8 = safe_search(r"Group1-8A\.\s*(.+)", content)
        groupX9 = safe_search(r"Group1-9A\.\s*(.+)", content)
        groupX10 = safe_search(r"Group1-10A\.\s*(.+)", content)
        groupX11 = safe_search(r"Group1-11A\.\s*(.+)", content)
        groupX12 = safe_search(r"Group1-12A\.\s*(.+)", content)
        groupX13 = safe_search(r"Group1-13A\.\s*(.+)", content)
        groupX14 = safe_search(r"Group1-14A\.\s*(.+)", content)
        groupX15 = safe_search(r"Group1-15A\.\s*(.+)", content)
        groupX16 = safe_search(r"Group1-16A\.\s*(.+)", content)
        groupX17 = safe_search(r"Group1-17A\.\s*(.+)", content)
        groupX18 = safe_search(r"Group1-18A\.\s*(.+)", content)
        groupX19 = safe_search(r"Group1-19A\.\s*(.+)", content)
        groupX20 = safe_search(r"Group1-20A\.\s*(.+)", content)
        groupX21 = safe_search(r"Group1-21A\.\s*(.+)", content)
        groupX22 = safe_search(r"Group1-22A\.\s*(.+)", content)
        groupX23 = safe_search(r"Group1-23A\.\s*(.+)", content)
        groupX24 = safe_search(r"Group1-24A\.\s*(.+)", content)




        # Return structured data
        return {
            "Trial Identification": f"Trial1-Info:{structured_data.get('id')}",
            "NCT#": nct_numberr,
            # "Total number of clinical trials" : nct_number,
            "Phase": phase,
            "Cancer Type": cancer_type,
            "Sponsor": sponsor,
            "Findings": findings,
            "Conclusions": conclusions,
            "Study Groups": study_groups,
            "Group Info": group_info,
            "GroupX1" : groupX1,
            "GroupX2" : groupX2,
            "GroupX3" : groupX3,
            "GroupX4" : groupX4,
            "GroupX5" : groupX5,
            "GroupX6" : groupX6,
            "GroupX7" : groupX7,
            "GroupX8" : groupX8,
            "GroupX9" : groupX9,
            "GroupX10" : groupX10,
            "GroupX11" : groupX11,
            "GroupX12" : groupX12,
            "GroupX13" : groupX13,
            "GroupX14" : groupX14,
            "GroupX15" : groupX15,
            "GroupX16" : groupX16,
            "GroupX17" : groupX17,
            "GroupX18" : groupX18,
            "GroupX19" : groupX19,
            "GroupX20" : groupX20,
            "GroupX21" : groupX21,
            "GroupX22" : groupX22,
            "GroupX23" : groupX23,
            "GroupX24" : groupX24,

            # Add more extracted group data here if needed
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
            # "Total number of clinical trials",
            "Phase",
            "Cancer Type",
            "Sponsor",
            "Findings",
            "Conclusions",
            "Study Groups",
            "Group Info",
            "GroupX1",
            "GroupX2",
            "GroupX3",
            "GroupX4",
            "GroupX5",
            "GroupX6",
            "GroupX7",
            "GroupX8",            
            "GroupX9",
            "GroupX10",
            "GroupX11",
            "GroupX12",
            "GroupX13",
            "GroupX14",
            "GroupX15",
            "GroupX16",
            "GroupX17",
            "GroupX18",
            "GroupX19",
            "GroupX20",
            "GroupX21",
            "GroupX22",
            "GroupX23",
            "GroupX24",
            
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

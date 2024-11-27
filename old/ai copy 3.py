import requests
import csv
import json
from xml.etree import ElementTree as ET

# PubMed Search API Parameters
pubmed_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
pubmed_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# OpenRouter LLM API
llm_api_url = "https://openrouter.ai/api/v1"  
llm_api_key = "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"

# Example search keyword
keyword = input("Enter the clinical trial keyword (e.g., Breast Cancer): ")

# Pagination control
total_pages = int(input("Enter the number of pages to scrape: "))

# Function to check available models and export to a file
def check_available_models():
    models_url = "https://openrouter.ai/api/v1/models"
    response = requests.get(models_url)
    
    if response.status_code == 200:
        models = response.json()
        # print("Available models:", models)
        
        # Save models to a text file
        with open("available_models.txt", "w") as file:
            file.write(json.dumps(models, indent=4))
        print("Models have been exported to 'available_models.txt'")
    else:
        print("Failed to fetch available models:", response.status_code)

# Fetch PubMed results
def fetch_pubmed_results(keyword, page_num):
    params = {
        'db': 'pubmed',
        'term': f'{keyword} AND "Randomized Controlled Trial"[pt]',
        'retstart': page_num * 10,
        'retmax': 10,
        'usehistory': 'y'
    }
    response = requests.get(pubmed_search_url, params=params)
    response.raise_for_status()  # Raise an error for HTTP errors
    
    print(f"Response for page {page_num}: {response.text}")  # Debug: print response
    return response.text

# Function to parse trial IDs from the XML response
def parse_trial_ids(xml_response):
    root = ET.fromstring(xml_response)
    return [id_elem.text for id_elem in root.find(".//IdList")]

# Fetch specific trial information
def fetch_trial_info(trial_id):
    params = {
        'db': 'pubmed',
        'id': trial_id,
        'rettype': 'abstract',
        'retmode': 'text'
    }
    response = requests.get(pubmed_fetch_url, params=params)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Error fetching trial info: {response.status_code}")
        return None

# Call LLM API for structured data
def call_llm_api(text_data):
    headers = {
        'Authorization': f'Bearer {llm_api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": "Meta: Llama 3.1 70B Instruct",  # Adjust based on available models
        "messages": [
            {
                "role": "user",
                "content": f"Please provide structured data for this trial: {text_data}"
            }
        ]
    }
    
    try:
        response = requests.post(llm_api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        return None  

# Save extracted data to CSV
def save_to_csv(trial_data, filename="clinical_trials.csv"):
    fieldnames = ["NCT Number", "Phase", "Cancer Type", "Sponsor", "Conclusions", "Study Groups", "Efficacy Data"]
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for data in trial_data:
            writer.writerow(data)

# Main script execution
if __name__ == "__main__":
    check_available_models()  # Check available models first and export them
    all_trials = []
    for page in range(total_pages):
        xml_data = fetch_pubmed_results(keyword, page)
        if xml_data:
            # Parse trial IDs
            trial_ids = parse_trial_ids(xml_data)
            print(f"Parsed trial IDs: {trial_ids}")  # Debug: Print parsed IDs
            for trial_id in trial_ids:
                trial_info = fetch_trial_info(trial_id)
                if trial_info:
                    print(f"\nFetched trial info for ID {trial_id}:")
                    print(trial_info)  # Print fetched trial abstract info
                    structured_data = call_llm_api(trial_info)
                    if structured_data:
                        print(f"Structured data for trial ID {trial_id}: {structured_data}")
                        all_trials.append(structured_data)

    # Save to CSV
    if all_trials:
        save_to_csv(all_trials)
        print(f"\nData for {len(all_trials)} trials has been saved to clinical_trials.csv")
    else:
        print("No trial data to save.")

import requests
from bs4 import BeautifulSoup
import csv
import json
import os

# PubMed Search API Parameters
pubmed_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
pubmed_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# OpenRouter LLM API
llm_api_url = "https://openrouter.ai/api/v1/chat/completions"  # Updated URL
# llm_api_key = os.getenv("OPENROUTER_API_KEY")  # Set this environment variable
llm_api_key = "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"


# Example search keyword
keyword = input("Enter the clinical trial keyword (e.g., Breast Cancer): ")

# Pagination control
total_pages = int(input("Enter the number of pages to scrape: "))

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
    return response.text

# Use 'lxml' parser when processing XML
def parse_clinical_trials(xml_data):
    soup = BeautifulSoup(xml_data, 'lxml-xml')
    trials = []
    for trial in soup.find_all('id'):
        trial_id = trial.text
        trials.append(trial_id)
    print(f"Parsed trial IDs: {trials}")  # Debug: Print parsed IDs
    return trials

# Fetch specific trial information
def fetch_trial_info(trial_id):
    params = {
        'db': 'pubmed',
        'id': trial_id,
        'rettype': 'abstract',
        'retmode': 'text'
    }
    response = requests.get(pubmed_fetch_url, params=params)
    response.raise_for_status()  # Raise an error for HTTP errors
    return response.text

# Call LLM API for structured data
def call_llm_api(text_data):
    headers = {
        'Authorization': f'Bearer {llm_api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": f"What insights can you provide about this trial? {text_data}"
            }
        ]
    }
    
    try:
        response = requests.post(llm_api_url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an error for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as err:
        print(f"Request failed: {err}")
        return None  # Return None if there's an error

# Save extracted data to CSV
def save_to_csv(trial_data, filename="clinical_trials.csv"):
    fieldnames = ["NCT Number", "Phase", "Cancer Type", "Sponsor", "Conclusions", "Study Groups", "Efficacy Data"]
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for data in trial_data:
            # Ensure data contains all necessary fields, providing defaults for missing fields
            writer.writerow({key: data.get(key, "N/A") for key in fieldnames})

# Main script execution
if __name__ == "__main__":
    all_trials = []
    for page in range(total_pages):
        html_data = fetch_pubmed_results(keyword, page)
        trial_ids = parse_clinical_trials(html_data)
        for trial_id in trial_ids:
            trial_info = fetch_trial_info(trial_id)
            print(f"\nFetched trial info for ID {trial_id}:")
            print(trial_info)  # Print fetched trial abstract info
            structured_data = call_llm_api(trial_info)
            if structured_data:
                print(f"Structured data for trial ID {trial_id}: {structured_data}")
                all_trials.append(structured_data)

    # Save to CSV
    save_to_csv(all_trials)
    print(f"\nData for {len(all_trials)} trials has been saved to clinical_trials.csv")

import requests
from bs4 import BeautifulSoup
import csv
import json

# PubMed Search API Parameters
pubmed_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
pubmed_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# OpenRouter LLM API
llm_api_url = "https://api.openrouter.ai/v1/completions"
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
    if response.status_code == 200:
        return response.text
    return None

# Parse PubMed Data
# def parse_clinical_trials(html_data):
#     soup = BeautifulSoup(html_data, 'html.parser')
#     trials = []
#     for trial in soup.find_all('docsum'):
#         trial_id = trial.find('id').text
#         trials.append(trial_id)
#     return trials



# Use 'lxml' parser when processing XML
def parse_clinical_trials(xml_data):
    soup = BeautifulSoup(xml_data, 'lxml')  # Use 'lxml' parser for XML data
    trials = []
    for trial in soup.find_all('docsum'):
        trial_id = trial.find('id').text
        trials.append(trial_id)
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
    if response.status_code == 200:
        return response.text
    return None

# Call LLM API for structured data
def call_llm_api(text_data):
    headers = {
        'Authorization': f'Bearer {llm_api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": "llama-3.1-70b",
        "prompt": f"<BEGIN PROMPT>{text_data}<END PROMPT>",
        "max_tokens": 2048,
        "temperature": 0.7
    }
    response = requests.post(llm_api_url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
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
    all_trials = []
    for page in range(total_pages):
        html_data = fetch_pubmed_results(keyword, page)
        trial_ids = parse_clinical_trials(html_data)
        for trial_id in trial_ids:
            trial_info = fetch_trial_info(trial_id)
            if trial_info:
                structured_data = call_llm_api(trial_info)
                all_trials.append(structured_data)

    save_to_csv(all_trials)

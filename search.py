import pandas as pd
from thefuzz import process

def search_siddha_names_from_excel(file_path, query, threshold=70, limit=20):
    search_data = []
    try:
        df = pd.read_excel(file_path, engine='xlrd')
        
        for index, row in df.iterrows():
            namc_term = row.get("NAMC_TERM")
            namc_code = row.get("NAMC_CODE")
            
            if pd.notna(namc_term) and pd.notna(namc_code):
                search_data.append((namc_term, namc_code))

    except FileNotFoundError:
        return []
    
    searchable_strings = [item[0] for item in search_data]
    
    matches = process.extractBests(query, searchable_strings, score_cutoff=threshold, limit=limit)
    
    final_results = []
    for match, score in matches:
        code = next((code for name, code in search_data if name == match), None)
        if code:
            final_results.append((match, code, score))
    
    return final_results

if __name__ == "__main__":
    file_name = "Data/NATIONAL SIDDHA MORBIDITY CODES.xls"
    
    user_query = input("Enter a name or term to search for: ")
    
    results = search_siddha_names_from_excel(file_name, user_query)
    
    if results:
        print("\n--- Search Results ---")
        for name, code, score in results:
            print(f"Name: {name}, Code: {code}, Similarity: {score}%")
    else:
        print("\nNo relevant matches found. Please try a different name.")

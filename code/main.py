import os
import time
import pandas as pd
from tqdm import tqdm

from agent import process_ticket

# Paths configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "support_tickets"))

PRIMARY_CSV_PATH = os.path.join(DATA_DIR, "support_tickets.csv")
FALLBACK_CSV_PATH = os.path.join(DATA_DIR, "sample_support_tickets.csv")
OUTPUT_CSV_PATH = os.path.join(DATA_DIR, "output.csv")

def main():
    print("Starting Orchestrator Evaluation Loop...")
    
    # 1. Data Ingestion
    if os.path.exists(PRIMARY_CSV_PATH):
        print(f"Loading primary tickets from {PRIMARY_CSV_PATH}")
        df = pd.read_csv(PRIMARY_CSV_PATH)
    elif os.path.exists(FALLBACK_CSV_PATH):
        print(f"Primary tickets not found. Falling back to {FALLBACK_CSV_PATH}")
        df = pd.read_csv(FALLBACK_CSV_PATH)
    else:
        print("Error: No support tickets CSV found.")
        return

    # Normalize column names to lowercase to be case-insensitive
    df.columns = df.columns.str.lower()

    total_tickets = len(df)
    print(f"Loaded {total_tickets} tickets for processing.")
    
    results = []
    
    # 2. Processing Loop
    try:
        # Wrap in tqdm for real-time progress bar
        for idx, row in tqdm(df.iterrows(), total=total_tickets, desc="Processing Tickets"):
            # Input Handling: Extract and handle missing/NaN values
            issue = str(row.get('issue', ''))
            subject = str(row.get('subject', ''))
            company = str(row.get('company', ''))
            
            # Clean up 'nan' string representation if pandas parsed empty cells as NaN
            if issue.lower() == 'nan': issue = ""
            if subject.lower() == 'nan': subject = ""
            if company.lower() == 'nan': company = ""
            
            # Agent Integration
            ticket_result = process_ticket(issue, subject, company)
            results.append(ticket_result)
            
            # Print status and request_type for real-time monitoring
            print(f"[Ticket {idx + 1}/{total_tickets}] -> Status: {ticket_result.get('status', 'N/A')} | Request Type: {ticket_result.get('request_type', 'N/A')}")
            
            # Rate Limiting (CRITICAL) - 15 RPM limits -> 4s between calls
            if idx < total_tickets - 1:
                time.sleep(4)
                
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Saving progress...")
    except Exception as e:
        print(f"\nUnexpected error during processing loop: {e}")
        print("Saving progress collected so far...")
    
    # 3. CSV Formatting & Export
    if not results:
        print("No results to save.")
        return
        
    print(f"\nProcessed {len(results)} tickets. Saving to CSV...")
    
    results_df = pd.DataFrame(results)
    
    # Ensure exact column order and presence
    expected_columns = ['status', 'product_area', 'response', 'justification', 'request_type']
    
    # Add any missing columns just in case the LLM or fallback failed catastrophically
    for col in expected_columns:
        if col not in results_df.columns:
            results_df[col] = ""
            
    # Keep strictly the required columns
    final_df = results_df[expected_columns]
    
    # Save without index
    final_df.to_csv(OUTPUT_CSV_PATH, index=False)
    print(f"Evaluation complete. Results saved to {OUTPUT_CSV_PATH}")

if __name__ == "__main__":
    main()

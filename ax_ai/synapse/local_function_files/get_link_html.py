import requests, html, re, lxml, json, sys
import pandas as pd
from bs4 import BeautifulSoup

def clean_html_content(raw_html):
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text)
    text = re.sub(r"<(br|p|div|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.strip()

def get_link_html(link_to_get):
    print("Start")
    xml_url = link_to_get
    headers = {
        "User-Agent": "jo boulement jo@gmx.at",
        "Accept-Encoding": "gzip, deflate"}
    response = requests.get(xml_url, headers=headers)
    extracted_data = ""

    soup = BeautifulSoup(response.content, features="xml")
    temp_soup = soup.get_text(strip=True)
    
    if len(temp_soup) > 524000:
        print(f"Warning: Character length ({len(temp_soup)}) exceeds limit. Cutting off...")
        final_context_payload = temp_soup[:524000]
    else:
        print("Success: Text fits safely within character estimates.")
        final_context_payload = temp_soup

    return str(final_context_payload).replace("[", "").replace("]", "")



def extract_section(start_regex, end_regex, section_name, full_text):
    starts = [m.start() for m in re.finditer(start_regex, full_text)]
    ends = [m.start() for m in re.finditer(end_regex, full_text)]
    
    if not starts or not ends:
        return f"[{section_name} not found: missing boundary markers]"
        
    # Bypass Table of Contents by taking the last/latest header match
    section_start = starts[-1] if len(starts) > 1 else starts[0]
    
    # Find the next immediate section end marker
    section_end = None
    for end in ends:
        if end > section_start:
            section_end = end
            break
            
    if section_end:
        return full_text[section_start:section_end].strip()
    else:
        # Fallback block slice if end marker fails
        return full_text[section_start:section_start + 60000].strip() + "\n...[Truncated Catch-all Block]..."

def get_10k_link_html(link_to_get):
    #input_url = sys.stdin.read().strip()

    headers = {"User-Agent": "LementAnalytics johnsmith@gmail.pt", "Accept-Encoding": "gzip, deflate"}
    response = requests.get(link_to_get, headers=headers, timeout=(10, 30))
    
    if response.status_code != 200:
        print(f"Failed to fetch document. Status code: {response.status_code}")
        return print(f"Failed to fetch document. Status code: {response.status_code}")

    soup = BeautifulSoup(response.content, features="xml")
    full_text = soup.get_text(separator=' ', strip=True)
    header_text = full_text[:50000]

    ### 2. Find Period Date 
    date_pattern = re.compile(r"ended[\s|]*([a-z]+\s+\d{1,2},?\s+\d{4})", re.IGNORECASE)
    date_match = date_pattern.search(header_text)
    period_ended = date_match.group(1) if date_match else "Unknown"    


    if "ANNUAL REPORT PURSUANT" in header_text:
        form_type = "10-K"
### Define Strict SEC Item Boundaries
### Item 1 -> Item 1A or Item 2
        item1_start = re.compile(r'Item\s+1\.?\s+Business' , re.IGNORECASE)
        item1_end = re.compile(r'Item\s+1A\.?\s+Risk\s+Factors|Item\s+2\.?\s+Properties', re.IGNORECASE)
### Item 1A -> Item 1B or Item 2
        item1a_start = re.compile(r'Item\s+1A\.?\s+Risk\s+Factors', re.IGNORECASE)
        item1a_end = re.compile(r'Item\s+1B\.?\s+Unresolved|Item\s+2\.?\s+Properties', re.IGNORECASE)  
### Item 8 Notes -> Item 9
### Anchors on the actual financial notes text inside Item 8, ending at Item 9
        item8_notes_start = re.compile(r'Notes\s+to\s+Consolidated\s+Financial\s+Statements|Notes\s+to\s+Financial\s+Statements', re.IGNORECASE)
        item8_notes_end = re.compile(r'Item\s+9\.?\s+Changes\s+in\s+and\s+Disagreements|Item\s+9A\.?\s+Controls', re.IGNORECASE)

    else:
        form_type = "10-Q"
### Define Strict SEC Item Boundaries for 10-Q
### Part I, Item 1 (Financial Statements) -> Item 2 (MD&A)
        item1_start = re.compile(r'Item\s+1\.?\s+Financial\s+Statements', re.IGNORECASE)
        item1_end = re.compile(r'Item\s+2\.?\s+Management\'s\s+Discussion\s+and\s+Analysis', re.IGNORECASE)

### Part II, Item 1A (Risk Factors) -> Item 2 or Item 3 (Unregistered Equity / Defaults)
### Note: Risk Factors are optional in 10-Q if there are no material updates, but structured under Part II if present.
        item1a_start = re.compile(r'Item\s+1A\.?\s+Risk\s+Factors', re.IGNORECASE)
        item1a_end = re.compile(r'Item\s+2\.?\s+Unregistered\s+Sales|Item\s+3\.?\s+Defaults|Item\s+4\.?\s+Mine\s+Safety', re.IGNORECASE)

### Item 1 Notes -> Item 2
### Anchors on the actual financial notes text inside Part I, Item 1, ending at Item 2 MD&A
        item8_notes_start = re.compile(r'Notes\s+to\s+(?:Condensed\s+)?Consolidated\s+Financial\s+Statements', re.IGNORECASE)
        item8_notes_end = re.compile(r'Item\s+2\.?\s+Management\'s\s+Discussion\s+and\s+Analysis', re.IGNORECASE)


### Extract all three items from the single text string
    data_payload = { "form_type": form_type, "period_ended": period_ended,
        "business_description": extract_section(item1_start, item1_end, "Item 1. Business", full_text),
        "risk_factors": extract_section(item1a_start, item1a_end, "Item 1A. Risk Factors", full_text),
        "financial_notes": extract_section(item8_notes_start, item8_notes_end, "Item 8 Financial Notes", full_text)
    }
        
    return print(json.dumps(data_payload))


def get_cik_fillings(cik, type):
    cik = str(cik).zfill(10)
    cik = "CIK"+str(cik)+".json"
    
    url = "http://data.sec.gov/submissions/"
    url = url+cik
    headers = {
        "User-Agent": "jo boulement jo@gmx.at",
        "Accept-Encoding": "gzip, deflate"}
    datafile = requests.get(url=url, headers=headers)
    links_lst = datafile.json()

    links_lst_df = pd.DataFrame.from_dict(links_lst['filings']['recent'])
    links_lst_df["accessionNumber"] = links_lst_df["accessionNumber"].str.replace("-", "")
    links_lst_df['link'] = 'https://www.sec.gov/Archives/edgar/data/'+ str(links_lst['cik'])+ '/' + links_lst_df['accessionNumber'] + "/" + links_lst_df['primaryDocument']

    links_lst_df = links_lst_df[['link', 'reportDate', 'filingDate', 'form']]
    links_lsts = links_lst_df[links_lst_df['form'] == type]

    return links_lsts['link'].to_list()

#temp_url = 'https://www.sec.gov/Archives/edgar/data/0000715957/000119312526063120/d-20251231.htm'

#print(get_10k_link_html(temp_url))


if __name__ == "__main__":
    # Ensure we got the minimum arguments: [file_path, function_name, url]
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Missing function name or URL arguments"}))
        sys.exit(1)

    function_name = sys.argv[1]
    try:  
        item_1 = sys.argv[2].strip('"\'') 
        item_2 = sys.argv[3]
    except:
        item_1 = sys.argv[2].strip('"\'')      

### functions with no input values or only 1 input value go in function_map, two values go in function_map_2, etc.
    function_map = {"get_10k_link_html": get_10k_link_html,
                    "get_link_html": get_link_html,}
    function_map_2 = {"get_cik_fillings": get_cik_fillings,}

    # Route dynamically
    if function_name in function_map:
        payload = function_map[function_name](item_1)
        print(json.dumps(payload))

    elif function_name in function_map_2:
        payload = function_map_2[function_name](item_1, item_2)
        print(json.dumps(payload))

    else:
        print(json.dumps({"error": f"Function '{function_name}' not found in file"}))

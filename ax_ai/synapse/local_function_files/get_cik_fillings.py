import requests, sys
import pandas as pd

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

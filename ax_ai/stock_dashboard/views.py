from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.forms.models import model_to_dict
from django.utils.safestring import mark_safe
from django.utils.html import escape

from axiom.views import send_task_to_model
from bots.models import model_connection
from synapse.models import *
from bots.models import *
from synapse.views import get_connection_data, get_local_connection_data, get_connection_data_w_input

from stock_dashboard import SEC_Data_Classes

from pathlib import Path
from sqlalchemy import create_engine
import pandas as pd
from dateutil.relativedelta import relativedelta
import numpy as np
import subprocess, json, re, os, sqlite3, requests, glob, markdown, ast, difflib, sys
import plotly.graph_objs as graph
from plotly.subplots import make_subplots
import plotly.io as plotly

def remove_zeros(df):
    max_date = max(df['end'])
    for i, e in enumerate(df['desc'].unique()):
        temp_count = df[df['desc']==e]
        if temp_count.shape[0] < 3:
            if max_date in temp_count['end'].values:
                e
            else:
                df = df[df['desc']!=e]
        else:
            e    
    return df

def convert_int(num):
    try:
        if "$-" in num:
            num = num.replace("$-", "")
            num = num.replace(",", "")
            num = float(num)*-1
        elif "$" in num:
            num = num.replace("$ ", "")
            num = num.replace(",", "")
            num = float(num)
    except:
        num = float(num)
    if type(num) == int or type(num) == float:
        if abs(num) >= 100 and abs(num) < 1000000:
            num_out = int(num)
            return "${:,.0f}".format(num_out)
        if abs(num) >= 1000 and abs(num) < 1000000:
            num_out = int(num/1000)
            return "${:,.0f}".format(num_out)+ "k"
        elif abs(num) >= 1000000:
            num_out = int(num/1000000)
            return "${:,.0f}".format(num_out)+ "m"
        else:
            num_out = int(num)
            return "${:,.0f}".format(num_out)

def make_plt_candle(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                vertical_spacing=0.03, subplot_titles=('Price', 'Volume'), 
                row_width=[0.2, 0.7])

    fig.add_trace(graph.Candlestick(x=df["datetime"], open=df["open"], high=df["high"],
                    low=df["low"], close=df["close"], name="Price"), 
                    row=1, col=1
    )
    fig.add_trace(graph.Bar(x=df['datetime'], y=df['volume'].astype(float), showlegend=False), row=2, col=1)


    fig.update_layout(
        paper_bgcolor="var(--bg-dark)",  
        plot_bgcolor="var(--bg)",         
        margin=dict(t=40, b=40, l=50, r=20),
        
        # Typography
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
            size=12,
            color="var(--text)"             # Muted slate color matching your CSS variables
        ),
        
        # Hover Interaction UI
        hovermode="x unified",          # Clean single tool-tip overlay over the x-axis
        hoverlabel=dict(
            bgcolor="var(--bg)",
            font_size=13,
            font_family="inherit",
            font_color = "var(--text)",
            bordercolor="var(--border)"
        ),
        
        # Clean Axis Configuration
        xaxis=dict(
            showgrid=True,
            gridcolor="var(--border-muted)",        # Ultra-faint gridlines
            linecolor="var(--border)",        # Solid base line
            showspikes=True,            # Crosshair guide line
            spikethickness=1,
            spikedash="dot",
            tickfont  = dict(color="var(--text)"),
            spikemode="across"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="var(--border-muted)",
            linecolor="var(--border)",
            tickfont  = dict(color="var(--text)"),
            tickformat="$,"             # Currency formatting helper (adjust as needed)
        ),
        
        # Legend Positioning (If your chart uses multiple traces)
        showlegend=True,
        legend=dict(
            orientation="h",            # Horizontal legend
            yanchor="bottom",
            y=1.02,                     # Position cleanly right above the chart grid
            xanchor="right",
            x=1,
            font=dict(color="var(--text)")
        )
    )

    #fig.update(layout_xaxis_rangeslider_visible=False)
    return plotly.to_html(fig, div_id='ticker_plt', config = {'responsive': True, 'displayModeBar': False})

def chunk_by_sentences(text, chunk_size=6):
    """Splits a large text block into chunks of X sentences."""
    if not text:
        return []
    # Splitting on sentence endings while keeping the punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    chunks = []
    for i in range(0, len(sentences), chunk_size):
        chunk = " ".join(sentences[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def get_inline_word_diff(old_line, new_line):
    """Performs word-by-word diff strictly within a single changed line."""
    # Split text into tokens but keep the spaces so formatting stays intact
    old_words = re.split(r'(\s+)', old_line)
    new_words = re.split(r'(\s+)', new_line)
    
    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    output = []
    
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == 'equal':
            output.append("".join(old_words[i1:i2]))
        elif opcode == 'replace':
            output.append(f"<del class='diff-del'>{''.join(old_words[i1:i2])}</del>")
            output.append(f"<ins class='diff-ins'>{''.join(new_words[j1:j2])}</ins>")
        elif opcode == 'delete':
            output.append(f"<del class='diff-del'>{''.join(old_words[i1:i2])}</del>")
        elif opcode == 'insert':
            output.append(f"<ins class='diff-ins'>{''.join(new_words[j1:j2])}</ins>")
            
    return "".join(output)

def generate_inline_diff(old_str, new_str, sentences_per_chunk=6):
    """
    Chunks large text blocks, compares them chunk-by-chunk like Git lines,
    and isolates word-by-word changes to prevent cascading blackouts.
    """
    # 1. Chunk both large text fields down into manageable 6-sentence paragraphs
    old_chunks = chunk_by_sentences(escape(old_str or ""), sentences_per_chunk)
    new_chunks = chunk_by_sentences(escape(new_str or ""), sentences_per_chunk)
    
    # 2. Use SequenceMatcher to find which paragraphs correspond to each other
    matcher = difflib.SequenceMatcher(None, old_chunks, new_chunks)
    html_output = []
    
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == 'equal':
            # Unchanged paragraphs are outputted cleanly as standard blocks
            for chunk in old_chunks[i1:i2]:
                html_output.append(f"<div class='diff-row diff-equal'>{chunk}</div>")
                
        elif opcode == 'delete':
            # Entire paragraph chunks were removed
            for chunk in old_chunks[i1:i2]:
                html_output.append(f"<div class='diff-row diff-line-del'><del>{chunk}</del></div>")
                
        elif opcode == 'insert':
            # Entire paragraph chunks were added
            for chunk in new_chunks[j1:j2]:
                html_output.append(f"<div class='diff-row diff-line-ins'><ins>{chunk}</ins></div>")
                
        elif opcode == 'replace':
            # A paragraph was modified. Instead of blacking out the whole chunk,
            # pair up the sub-changes so they sit next to/within each other.
            old_sub_blocks = old_chunks[i1:i2]
            new_sub_blocks = new_chunks[j1:j2]
            
            # Zip them together to compare paired sentences sequentially
            max_len = max(len(old_sub_blocks), len(new_sub_blocks))
            for idx in range(max_len):
                o_block = old_sub_blocks[idx] if idx < len(old_sub_blocks) else ""
                n_block = new_sub_blocks[idx] if idx < len(new_sub_blocks) else ""
                
                if o_block and n_block:
                    # Both old and new exist, isolate the exact word edits inside it
                    inline_diff = get_inline_word_diff(o_block, n_block)
                    html_output.append(f"<div class='diff-row diff-line-mod'>{inline_diff}</div>")
                elif o_block:
                    html_output.append(f"<div class='diff-row diff-line-del'><del>{o_block}</del></div>")
                elif n_block:
                    html_output.append(f"<div class='diff-row diff-line-ins'><ins>{n_block}</ins></div>")
                    
    return mark_safe("\n".join(html_output))

def chunk_text(text, sentences_per_paragraph=6):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    paragraphs = []
    for i in range(0, len(sentences), sentences_per_paragraph):
        para = " ".join(sentences[i:i + sentences_per_paragraph])
        paragraphs.append(f"<p>{para}</p>")
        
    return "".join(paragraphs)


class function_management_dashboard(View):
    def get(self, request, stock_ticker=None):
        context = {}
        ticker_cik_list = get_connection_data(connection_functions.objects.get(connection_function_name = "company_tickerscsv"))
        ticker_cik_list_values = pd.DataFrame(ticker_cik_list['temp_data'])

        if stock_ticker != None:
            ticker_to_display = ticker_cik_list_values[ticker_cik_list_values['ticker'] == str(stock_ticker).upper()].iloc[0].to_dict()
        else:
            ticker_to_display = ticker_cik_list_values.iloc[0].to_dict()

        all_links = []
        ticker_to_display['local_function_name'] = "get_cik_fillings"
        ticker_to_display['__input__cik'] = ticker_to_display["cik_str"]
        ticker_to_display['__input__type'] = "10-K"
        k10_link = get_local_connection_data(ticker_to_display)
        k10_links_list = k10_link.stdout.replace("[", "").replace("]", "").replace("'", "").split(",")
        all_links.extend(k10_links_list[:2])

        ticker_to_display['__input__type'] = "10-Q"
        q10_link = get_local_connection_data(ticker_to_display)
        q10_links_list = q10_link.stdout.replace("[", "").replace("]", "").replace("'", "").split(",")
        #all_links.extend(q10_links_list[:6])

        all_links_data = []
        for i, report_link in enumerate(all_links):
            temp_data = {"local_function_name": "get_10k_link_html",
                         "__input__link": str(report_link).replace("'", "").replace('"', "")}
            temp_data_info = get_local_connection_data(temp_data)
            temp_text = str(temp_data_info.stdout)
            start = temp_text.find("{")
            end = temp_text.rfind("}")

            if start != -1 and end != -1 and end > start:
                result_text = temp_text[start:end + 1]
            else:
                result_text = temp_data_info.stdout

            try:
                temp_data_info_dict = json.load(result_text)
            except:
                temp_data_info_dict = ast.literal_eval(result_text)

            temp_data_info_dict['business_description'] = chunk_text(temp_data_info_dict['business_description'])
            temp_data_info_dict['risk_factors'] = chunk_text(temp_data_info_dict['risk_factors'])
            temp_data_info_dict['financial_notes'] = chunk_text(temp_data_info_dict['financial_notes'])

            all_links_data.append(temp_data_info_dict)

        compare_view_data = {"form_type":"compare", "period_ended":f"{all_links_data[0]['period_ended']} vs {all_links_data[1]['period_ended']}"}
        # generate_inline_diff looks better with old first, new second value
        compare_view_data['business_description'] = generate_inline_diff(all_links_data[1]['business_description'], all_links_data[0]['business_description'])
        compare_view_data['financial_notes'] = generate_inline_diff(all_links_data[1]['financial_notes'], all_links_data[0]['financial_notes'])
        compare_view_data['risk_factors'] = generate_inline_diff(all_links_data[1]['risk_factors'], all_links_data[0]['risk_factors'])

        all_links_data.append(compare_view_data)

        cwd = os.getcwd()
        ticker_cik_list = get_connection_data(connection_functions.objects.get(connection_function_name = "company_tickerscsv"))
        tickers = pd.DataFrame(ticker_cik_list['temp_data'])
        temptck = str(ticker_to_display['ticker']).upper()

        fig_plt = graph.Figure()
        rq = dict(request.POST)

        if temptck in list(tickers['ticker']):
            data = SEC_Data_Classes.getSECData(str(temptck)).getData()
            get_cik_data = get_connection_data_w_input(connection_functions.objects.get(connection_function_name = "twelvedata candle data"), {"ticker":temptck, "interval":"1day", "size":"252" })
            tmp_p_df = pd.DataFrame(get_cik_data['temp_data']['values'])

            ft_week_h = tmp_p_df[tmp_p_df['close'] == max(tmp_p_df['close'])]['close'].iloc[0]
            ft_week_l = tmp_p_df[tmp_p_df['close'] == min(tmp_p_df['close'])]['close'].iloc[0]
            ft_week_close = tmp_p_df[tmp_p_df['datetime'] == max(tmp_p_df['datetime'])]['close'].iloc[0]
            ft_week_open = tmp_p_df[tmp_p_df['datetime'] == max(tmp_p_df['datetime'])]['open'].iloc[0]
            ft_week_date = tmp_p_df[tmp_p_df['datetime'] == max(tmp_p_df['datetime'])]['datetime'].iloc[0]
            tmp_p_plt = make_plt_candle(tmp_p_df)
            current_market_price = tmp_p_df.loc[tmp_p_df['datetime'] == max(tmp_p_df['datetime'])]
            tempname = data['entityName']
            dfdata = pd.DataFrame()
            dataframe = pd.json_normalize(data['facts']['us-gaap'])
            for row in dataframe.columns[dataframe.columns.str.contains('.units')]:
                df_tmp = pd.json_normalize(dataframe[row][0])
                df_tmp['desc'] = row
                dfdata = pd.concat([df_tmp, dfdata], axis=0)
            
            dfdata = dfdata[dfdata['form']=='10-K']
            dfdata = dfdata[dfdata['fp']=='FY']
            dfdata = remove_zeros(dfdata)
            raw_data = dfdata
            NumOfCommonShares = dfdata[dfdata['desc'].str.contains('.shares')]
            NumOfCommonShares = NumOfCommonShares[~NumOfCommonShares['desc'].str.contains('Compensation')]
            PerShare = NumOfCommonShares[NumOfCommonShares['desc'].str.contains('.USD/shares')]
            NumOfCommonShares = NumOfCommonShares[~NumOfCommonShares['desc'].str.contains('.USD/shares')]
            PerShare['val'] = PerShare['val'].map('${:,.2f}'.format)
            NumOfCommonShares['val'] = NumOfCommonShares['val'].map('{:,.0f}'.format)
            NumOfCommonShares = NumOfCommonShares.pivot_table(values = 'val', 
                                                            index = ['desc'], 
                                                            columns = NumOfCommonShares['end'],
                                                            fill_value = '0', 
                                                            aggfunc='max')
            NumOfCommonShares = NumOfCommonShares[NumOfCommonShares.columns[::-1]]
            NumOfCommonShares = NumOfCommonShares.reset_index()
            PerShare = PerShare.pivot_table(values = 'val', 
                                            index = ['desc'], 
                                            columns = PerShare['end'],
                                            fill_value = '0', 
                                            aggfunc='max')
            PerShare = PerShare[PerShare.columns[::-1]]
            PerShare = PerShare.reset_index()

            links_lst = SEC_Data_Classes.getSECData(str(temptck)).getInfo()
            other_info = {}
            #pd.DataFrame.from_dict(links_lst)
            for i,e in enumerate(links_lst.keys()):
                if e == 'fillings':
                    print('yes')
                else:
                    other_info[str(e)] = links_lst[e]
            links_lst_df = pd.DataFrame.from_dict(links_lst['filings']['recent'])
            links_lst_df["accessionNumber"] = links_lst_df["accessionNumber"].str.replace("-", "")
            links_lst_df['link'] = 'https://www.sec.gov/Archives/edgar/data/'+ str(links_lst['cik'])+ '/' + links_lst_df['accessionNumber'] + "/" + links_lst_df['primaryDocument']

            links_lst_df = links_lst_df[['link', 'reportDate', 'filingDate', 'form']]
            links_lsts = []
            for i, e in enumerate(links_lst_df['form'].unique()):
                links_lsts.append({'name':e, 'dt':links_lst_df[links_lst_df['form'] == e].to_dict('records')})
            
            if len(other_info['formerNames'])>0:
                for i, e in enumerate(other_info['formerNames']):
                    other_info['formerNames'][i]['from'] = e['from'].split("T")[0]
                    other_info['formerNames'][i]['to'] = e['to'].split("T")[0]

            dfdata = dfdata[dfdata['desc'].str.contains('.units')]            

            is_list = ['Revenue', 'CostOfGoods', 'Profit', 'Admin*Selling', 'NetIncome']
            bsa_list = ['CashEquivalent', 'Accounts*Recievable', 'Inventory', 'AssetsCurrent', 'PropertyPlantAndEquipmentN', 'AssetsNon', 'Assets.units.USD']
            bsl_list = ['LongTermDebt~Proceeds', 'LiabilitiesC', 'Liabilities.~Equity', 'Equity~Liabilities']
            cf_list = ['CashEquivalent', 'NetCash*Operating', 'NetCash*Financing', 'NetCash*Investing']
            info_list = ['Revenue.', 'NetIncome', 'CashEquivalent', 'Assets.', 'LongTermDebt~Proceeds', 'Liabilities.~Equity', 'DividendsPer', 'EarningsPer']
            incomeStatement = pd.DataFrame()
            BalanceSheetA = pd.DataFrame()
            BalanceSheetL = pd.DataFrame()
            CashFlow = pd.DataFrame()
            info_df = pd.DataFrame()

            for x, lst in enumerate([is_list, bsa_list, bsl_list, cf_list, info_list]):
                statement = pd.DataFrame()
                for i, e in enumerate(lst):
                    if '*' in e:
                        ez = e.split('*')
                        e1 = ez[0]
                        e2 = ez[1]
                        item = dfdata[dfdata['desc'].str.contains(e1) & dfdata['desc'].str.contains(e2)]
                        if len(item) == 0:
                            item1 = dfdata[dfdata['desc'].str.contains(e1)]
                            item2 = dfdata[dfdata['desc'].str.contains(e2)]
                            if len(item1) == len(item2):
                                item = item1
                            else:
                                item = item1
                                item2 = item2.sort_values('val').drop_duplicates(subset='end', keep='last')
                                item2 = item2.sort_values('end')
                                item2 = item2[['desc', 'val', 'end']]
                                item2.index = item2['end']
                                if lst == bsl_list:
                                    item2['rnkNum'] = i+100.5
                                else:
                                    item2['rnkNum'] = i+0.5
                                item2['rnk'] = e2
                                statement = pd.concat([statement, item2])
                    elif '~' in e:
                        ez = e.split('~')
                        e1 = ez[0]
                        e2 = ez[1]
                        item = dfdata[dfdata['desc'].str.contains(e1)]
                        item = item[~item['desc'].str.contains(e2)]
                    else:
                        item = dfdata[dfdata['desc'].str.contains(e)]
                    item = item.sort_values('val').drop_duplicates(subset='end', keep='last')
                    item = item.sort_values('end')
                    item = item[['desc', 'val', 'end']]
                    item.index = item['end']
                    if lst == bsl_list:
                        item['rnkNum'] = i+100
                    else:
                        item['rnkNum'] = i
                    item['rnk'] = e
                    statement = pd.concat([statement, item])
                if lst == info_list:
                    statement['val'] = statement['val'].map('${: ,.2f}'.format)
                else:
                    statement['val'] = statement['val'].map('${: ,.0f}'.format)
                statementp = statement.pivot_table(values = 'val', 
                                                    index = ['rnkNum', 'desc'], 
                                                    columns = statement.index,
                                                    fill_value = '0', 
                                                    aggfunc='sum')
                
                if lst == is_list:
                    incomeStatement = statementp
                    incomeStatement = incomeStatement[incomeStatement.columns[::-1]]
                    incomeStatement = incomeStatement.reset_index()
                    incomeStatement = incomeStatement.drop(columns=['rnkNum'])
                elif lst == bsa_list:
                    BalanceSheetA = statementp
                elif lst == bsl_list:
                    BalanceSheetL = statementp
                elif lst == cf_list:
                    CashFlow = statementp
                    CashFlow = CashFlow[CashFlow.columns[::-1]]
                    CashFlow = CashFlow.reset_index()
                    CashFlow = CashFlow.drop(columns=['rnkNum'])
                elif lst == info_list:
                    info_df = statement

            raw_data = raw_data.sort_values('end')
            raw_data_list = raw_data['desc'].unique()
            try:
                for i, e in enumerate(fig_plt_view):
                    fig_plt_df = raw_data[raw_data['desc']==e]
                    fig_plt_view_temp = e.replace('.', ' ')
                    fig_plt_df.index = fig_plt_df['end']
                    fig_plt_df['val'] = pd.to_numeric(fig_plt_df['val'])
                    fig_plt_df = fig_plt_df.sort_values(by=['val'])
                    fig_plt_df = fig_plt_df.drop_duplicates('end', keep='first')
                    fig_plt_df = fig_plt_df.loc[:, ['val']]
                    fig_plt_df = fig_plt_df.rename(columns={"val": fig_plt_view_temp})
                    new_line = graph.Bar(x=fig_plt_df.index.tolist(), y=pd.to_numeric(fig_plt_df[fig_plt_df.columns[0]]), name=str(fig_plt_df.columns[0]))
                    fig_plt.add_trace(new_line)
            except:
                fig_plt_view = ['RevenueFromContractWithCustomerExcludingAssessedTax.units.USD', 'NetIncomeLoss.units.USD']
                for i, e in enumerate(fig_plt_view):
                    fig_plt_df = raw_data[raw_data['desc']==e]
                    fig_plt_view_temp = e.replace('.', ' ')
                    fig_plt_df.index = fig_plt_df['end']
                    fig_plt_df['val'] = pd.to_numeric(fig_plt_df['val'])
                    fig_plt_df = fig_plt_df.sort_values(by=['val'])
                    fig_plt_df = fig_plt_df.drop_duplicates('end', keep='first')
                    fig_plt_df = fig_plt_df.loc[:, ['val']]
                    fig_plt_df = fig_plt_df.rename(columns={"val": fig_plt_view_temp})
                    new_line = graph.Bar(x=fig_plt_df.index.tolist(), y=pd.to_numeric(fig_plt_df[fig_plt_df.columns[0]]), name=str(fig_plt_df.columns[0]))
                    fig_plt.add_trace(new_line)
            
            
            fig_plt.update_layout(xaxis=dict(rangeslider=dict(visible=True)))
            fig_plt.update_layout(legend=dict(yanchor="top", y=1.35, xanchor="left", x=-0.05))
            fig_plt.update_layout(showlegend=True)
            
            fig_plt_1 = plotly.to_html(fig_plt, full_html=False, include_plotlyjs='cdn', config = {'responsive': True, 'displayModeBar': False})
            fig_plt_2 = plotly.to_html(fig_plt, full_html=False, include_plotlyjs='cdn', config = {'responsive': True, 'displayModeBar': False})
            
            raw_data['val'] = raw_data['val'].apply(convert_int)
            raw_data = raw_data.pivot_table(values='val', index=['desc'], columns=['end'], fill_value="0", aggfunc='max')
            raw_data = raw_data[raw_data.columns[::-1]]
            raw_data = raw_data.reset_index()
            BalanceSheet = pd.concat([BalanceSheetA, BalanceSheetL], axis=0)
            BalanceSheet = BalanceSheet.dropna(axis=1)
            BalanceSheet = BalanceSheet[BalanceSheet.columns[::-1]]
            BalanceSheet = BalanceSheet.reset_index()
            BalanceSheet = BalanceSheet.drop(columns=['rnkNum'])

            quick_info = []
            top_two_dates = pd.to_datetime(info_df["end"]).drop_duplicates().nlargest(2)
            tmp_df_val = info_df[pd.to_datetime(info_df["end"]).isin(top_two_dates)]

            date_cols = [col for col in tmp_df_val.columns if col not in ["desc", "rnkNum"]]
            tmp_df_val["desc"] = tmp_df_val["desc"].str.split(".").str[0].str.slice(0, 16)
            tmp_df_val["val"] = tmp_df_val["val"].apply(convert_int)
            df_flat = tmp_df_val.reset_index(drop=True)
            pivoted_df = df_flat.pivot_table(index=["desc", "rnkNum"], columns="end", values="val", aggfunc="first")
            pivoted_df = pivoted_df.sort_values("rnkNum").reset_index(level="rnkNum", drop=True)
            pivoted_df.columns.name = None
            pivoted_df.index.name = None
            col_0 = pd.to_numeric(pivoted_df.iloc[:, 0].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce')
            col_1 = pd.to_numeric(pivoted_df.iloc[:, 1].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce')
            pivoted_df['diff'] = ((col_1 - col_0) / col_0 * 100).map('{:.2f}%'.format)
            quick_info = pivoted_df.to_html(classes="table summary-table")

            context = {'ticker': temptck,
                        'name': tempname,
                        'categories': other_info,
                        'high_low_52w': {'high':round(float(ft_week_h), 2), 
                                        'low':round(float(ft_week_l), 2),
                                        'high_to_close':round(100*((float(ft_week_h)-float(ft_week_close))/float(ft_week_close)), 2),
                                        'open_to_close':round(100*((float(ft_week_open)-float(ft_week_close))/float(ft_week_close)), 2),
                                        'close':round(float(ft_week_close), 2),
                                        'low_to_close':round(100*((float(ft_week_l)-float(ft_week_close))/float(ft_week_close)), 2),
                                        'date':ft_week_date},
                        'incomeStatement': incomeStatement.to_html(classes='table', index=False),
                        'balanceSheet': BalanceSheet.to_html(classes='table', index=False),
                        'cashFlow': CashFlow.to_html(classes='table', index=False),
                        'commonShareouts': NumOfCommonShares.to_html(classes='table', index=False),
                        'perShare': PerShare.to_html(classes='table', index=False),
                        'rawData': raw_data.to_html(classes='table', table_id='raw_data', index=False),
                        'currentPrice': current_market_price.to_html(classes='table'),
                        'price_plt':tmp_p_plt,
                        'links_lst': links_lsts,
                        'quick_info': quick_info,
                        'raw_data_list':raw_data_list,
                        'fig_plt':fig_plt_1,
                        'fig_plt_summary':fig_plt_2,}
            if 'fig_plt_option' in rq:
                context['financials_chart'] = 'yes'
           
        else:
            context = {'ticker': 'Not available',}

        context['links'] = all_links
        context['all_links_data'] = all_links_data
        return render(request, 'stock_dashboard/stock_dashboard.html', context)

    def post(self, request, stock_ticker=None):
        context = {}
        ticker_cik_list = get_connection_data(connection_functions.objects.get(connection_function_name = "company_tickerscsv"))
        ticker_cik_list_values = pd.DataFrame(ticker_cik_list['temp_data'])

        if stock_ticker != None:
            ticker_to_display = ticker_cik_list_values[ticker_cik_list_values['ticker'] == str(stock_ticker).upper()].iloc[0].to_dict()
        else:
            ticker_to_display = ticker_cik_list_values.iloc[0].to_dict()

        all_links = []
        ticker_to_display['local_function_name'] = "get_cik_fillings"
        ticker_to_display['__input__cik'] = ticker_to_display["cik_str"]
        ticker_to_display['__input__type'] = "10-K"
        k10_link = get_local_connection_data(ticker_to_display)
        k10_links_list = k10_link.stdout.replace("[", "").replace("]", "").replace("'", "").split(",")
        all_links.extend(k10_links_list[:2])

        ticker_to_display['__input__type'] = "10-Q"
        q10_link = get_local_connection_data(ticker_to_display)
        q10_links_list = q10_link.stdout.replace("[", "").replace("]", "").replace("'", "").split(",")
        #all_links.extend(q10_links_list[:6])

        all_links_data = []
        for i, report_link in enumerate(all_links):
            temp_data = {"local_function_name": "get_10k_link_html",
                            "__input__link": str(report_link).replace("'", "").replace('"', "")}
            temp_data_info = get_local_connection_data(temp_data)
            temp_text = str(temp_data_info.stdout)
            start = temp_text.find("{")
            end = temp_text.rfind("}")

            if start != -1 and end != -1 and end > start:
                result_text = temp_text[start:end + 1]
            else:
                result_text = temp_data_info.stdout

            try:
                temp_data_info_dict = json.load(result_text)
            except:
                temp_data_info_dict = ast.literal_eval(result_text)

            temp_data_info_dict['business_description'] = chunk_text(temp_data_info_dict['business_description'])
            temp_data_info_dict['risk_factors'] = chunk_text(temp_data_info_dict['risk_factors'])
            temp_data_info_dict['financial_notes'] = chunk_text(temp_data_info_dict['financial_notes'])

            all_links_data.append(temp_data_info_dict)

        compare_view_data = {"form_type":"compare", "period_ended":f"{all_links_data[0]['period_ended']} vs {all_links_data[1]['period_ended']}"}
        # generate_inline_diff looks better with old first, new second value
        compare_view_data['business_description'] = generate_inline_diff(all_links_data[1]['business_description'], all_links_data[0]['business_description'])
        compare_view_data['financial_notes'] = generate_inline_diff(all_links_data[1]['financial_notes'], all_links_data[0]['financial_notes'])
        compare_view_data['risk_factors'] = generate_inline_diff(all_links_data[1]['risk_factors'], all_links_data[0]['risk_factors'])

        all_links_data.append(compare_view_data)

        cwd = os.getcwd()
        ticker_cik_list = get_connection_data(connection_functions.objects.get(connection_function_name = "company_tickerscsv"))
        tickers = pd.DataFrame(ticker_cik_list['temp_data'])
        temptck = str(ticker_to_display['ticker']).upper()

        fig_plt = graph.Figure()
        rq = dict(request.POST)

        if temptck in list(tickers['ticker']):
            data = SEC_Data_Classes.getSECData(str(temptck)).getData()
            get_cik_data = get_connection_data_w_input(connection_functions.objects.get(connection_function_name = "twelvedata candle data"), {"ticker":temptck, "interval":"1day", "size":"252" })
            tmp_p_df = pd.DataFrame(get_cik_data['temp_data']['values'])

            ft_week_h = tmp_p_df[tmp_p_df['close'] == max(tmp_p_df['close'])]['close'].iloc[0]
            ft_week_l = tmp_p_df[tmp_p_df['close'] == min(tmp_p_df['close'])]['close'].iloc[0]
            ft_week_close = tmp_p_df[tmp_p_df['datetime'] == max(tmp_p_df['datetime'])]['close'].iloc[0]
            ft_week_open = tmp_p_df[tmp_p_df['datetime'] == max(tmp_p_df['datetime'])]['open'].iloc[0]
            ft_week_date = tmp_p_df[tmp_p_df['datetime'] == max(tmp_p_df['datetime'])]['datetime'].iloc[0]
            tmp_p_plt = make_plt_candle(tmp_p_df)
            current_market_price = tmp_p_df.loc[tmp_p_df['datetime'] == max(tmp_p_df['datetime'])]
            tempname = data['entityName']
            dfdata = pd.DataFrame()
            dataframe = pd.json_normalize(data['facts']['us-gaap'])
            for row in dataframe.columns[dataframe.columns.str.contains('.units')]:
                df_tmp = pd.json_normalize(dataframe[row][0])
                df_tmp['desc'] = row
                dfdata = pd.concat([df_tmp, dfdata], axis=0)
            
            dfdata = dfdata[dfdata['form']=='10-K']
            dfdata = dfdata[dfdata['fp']=='FY']
            dfdata = remove_zeros(dfdata)
            raw_data = dfdata
            NumOfCommonShares = dfdata[dfdata['desc'].str.contains('.shares')]
            NumOfCommonShares = NumOfCommonShares[~NumOfCommonShares['desc'].str.contains('Compensation')]
            PerShare = NumOfCommonShares[NumOfCommonShares['desc'].str.contains('.USD/shares')]
            NumOfCommonShares = NumOfCommonShares[~NumOfCommonShares['desc'].str.contains('.USD/shares')]
            PerShare['val'] = PerShare['val'].map('${:,.2f}'.format)
            NumOfCommonShares['val'] = NumOfCommonShares['val'].map('{:,.0f}'.format)
            NumOfCommonShares = NumOfCommonShares.pivot_table(values = 'val', 
                                                            index = ['desc'], 
                                                            columns = NumOfCommonShares['end'],
                                                            fill_value = '0', 
                                                            aggfunc='max')
            NumOfCommonShares = NumOfCommonShares[NumOfCommonShares.columns[::-1]]
            NumOfCommonShares = NumOfCommonShares.reset_index()
            PerShare = PerShare.pivot_table(values = 'val', 
                                            index = ['desc'], 
                                            columns = PerShare['end'],
                                            fill_value = '0', 
                                            aggfunc='max')
            PerShare = PerShare[PerShare.columns[::-1]]
            PerShare = PerShare.reset_index()

            links_lst = SEC_Data_Classes.getSECData(str(temptck)).getInfo()
            other_info = {}
            #pd.DataFrame.from_dict(links_lst)
            for i,e in enumerate(links_lst.keys()):
                if e == 'fillings':
                    print('yes')
                else:
                    other_info[str(e)] = links_lst[e]
            links_lst_df = pd.DataFrame.from_dict(links_lst['filings']['recent'])
            links_lst_df["accessionNumber"] = links_lst_df["accessionNumber"].str.replace("-", "")
            links_lst_df['link'] = 'https://www.sec.gov/Archives/edgar/data/'+ str(links_lst['cik'])+ '/' + links_lst_df['accessionNumber'] + "/" + links_lst_df['primaryDocument']

            links_lst_df = links_lst_df[['link', 'reportDate', 'filingDate', 'form']]
            links_lsts = []
            for i, e in enumerate(links_lst_df['form'].unique()):
                links_lsts.append({'name':e, 'dt':links_lst_df[links_lst_df['form'] == e].to_dict('records')})
            
            if len(other_info['formerNames'])>0:
                for i, e in enumerate(other_info['formerNames']):
                    other_info['formerNames'][i]['from'] = e['from'].split("T")[0]
                    other_info['formerNames'][i]['to'] = e['to'].split("T")[0]

            dfdata = dfdata[dfdata['desc'].str.contains('.units')]            

            is_list = ['Revenue', 'CostOfGoods', 'Profit', 'Admin*Selling', 'NetIncome']
            bsa_list = ['CashEquivalent', 'Accounts*Recievable', 'Inventory', 'AssetsCurrent', 'PropertyPlantAndEquipmentN', 'AssetsNon', 'Assets.units.USD']
            bsl_list = ['LongTermDebt~Proceeds', 'LiabilitiesC', 'Liabilities.~Equity', 'Equity~Liabilities']
            cf_list = ['CashEquivalent', 'NetCash*Operating', 'NetCash*Financing', 'NetCash*Investing']
            info_list = ['Revenue.', 'NetIncome', 'CashEquivalent', 'Assets.', 'LongTermDebt~Proceeds', 'Liabilities.~Equity', 'DividendsPer', 'EarningsPer']
            incomeStatement = pd.DataFrame()
            BalanceSheetA = pd.DataFrame()
            BalanceSheetL = pd.DataFrame()
            CashFlow = pd.DataFrame()
            info_df = pd.DataFrame()

            for x, lst in enumerate([is_list, bsa_list, bsl_list, cf_list, info_list]):
                statement = pd.DataFrame()
                for i, e in enumerate(lst):
                    if '*' in e:
                        ez = e.split('*')
                        e1 = ez[0]
                        e2 = ez[1]
                        item = dfdata[dfdata['desc'].str.contains(e1) & dfdata['desc'].str.contains(e2)]
                        if len(item) == 0:
                            item1 = dfdata[dfdata['desc'].str.contains(e1)]
                            item2 = dfdata[dfdata['desc'].str.contains(e2)]
                            if len(item1) == len(item2):
                                item = item1
                            else:
                                item = item1
                                item2 = item2.sort_values('val').drop_duplicates(subset='end', keep='last')
                                item2 = item2.sort_values('end')
                                item2 = item2[['desc', 'val', 'end']]
                                item2.index = item2['end']
                                if lst == bsl_list:
                                    item2['rnkNum'] = i+100.5
                                else:
                                    item2['rnkNum'] = i+0.5
                                item2['rnk'] = e2
                                statement = pd.concat([statement, item2])
                    elif '~' in e:
                        ez = e.split('~')
                        e1 = ez[0]
                        e2 = ez[1]
                        item = dfdata[dfdata['desc'].str.contains(e1)]
                        item = item[~item['desc'].str.contains(e2)]
                    else:
                        item = dfdata[dfdata['desc'].str.contains(e)]
                    item = item.sort_values('val').drop_duplicates(subset='end', keep='last')
                    item = item.sort_values('end')
                    item = item[['desc', 'val', 'end']]
                    item.index = item['end']
                    if lst == bsl_list:
                        item['rnkNum'] = i+100
                    else:
                        item['rnkNum'] = i
                    item['rnk'] = e
                    statement = pd.concat([statement, item])
                if lst == info_list:
                    statement['val'] = statement['val'].map('${: ,.2f}'.format)
                else:
                    statement['val'] = statement['val'].map('${: ,.0f}'.format)
                statementp = statement.pivot_table(values = 'val', 
                                                    index = ['rnkNum', 'desc'], 
                                                    columns = statement.index,
                                                    fill_value = '0', 
                                                    aggfunc='sum')
                
                if lst == is_list:
                    incomeStatement = statementp
                    incomeStatement = incomeStatement[incomeStatement.columns[::-1]]
                    incomeStatement = incomeStatement.reset_index()
                    incomeStatement = incomeStatement.drop(columns=['rnkNum'])
                elif lst == bsa_list:
                    BalanceSheetA = statementp
                elif lst == bsl_list:
                    BalanceSheetL = statementp
                elif lst == cf_list:
                    CashFlow = statementp
                    CashFlow = CashFlow[CashFlow.columns[::-1]]
                    CashFlow = CashFlow.reset_index()
                    CashFlow = CashFlow.drop(columns=['rnkNum'])
                elif lst == info_list:
                    info_df = statement

            raw_data = raw_data.sort_values('end')
            raw_data_list = raw_data['desc'].unique()
            try:
                for i, e in enumerate(fig_plt_view):
                    fig_plt_df = raw_data[raw_data['desc']==e]
                    fig_plt_view_temp = e.replace('.', ' ')
                    fig_plt_df.index = fig_plt_df['end']
                    fig_plt_df['val'] = pd.to_numeric(fig_plt_df['val'])
                    fig_plt_df = fig_plt_df.sort_values(by=['val'])
                    fig_plt_df = fig_plt_df.drop_duplicates('end', keep='first')
                    fig_plt_df = fig_plt_df.loc[:, ['val']]
                    fig_plt_df = fig_plt_df.rename(columns={"val": fig_plt_view_temp})
                    new_line = graph.Bar(x=fig_plt_df.index.tolist(), y=pd.to_numeric(fig_plt_df[fig_plt_df.columns[0]]), name=str(fig_plt_df.columns[0]))
                    fig_plt.add_trace(new_line)
            except:
                fig_plt_view = ['RevenueFromContractWithCustomerExcludingAssessedTax.units.USD', 'NetIncomeLoss.units.USD']
                for i, e in enumerate(fig_plt_view):
                    fig_plt_df = raw_data[raw_data['desc']==e]
                    fig_plt_view_temp = e.replace('.', ' ')
                    fig_plt_df.index = fig_plt_df['end']
                    fig_plt_df['val'] = pd.to_numeric(fig_plt_df['val'])
                    fig_plt_df = fig_plt_df.sort_values(by=['val'])
                    fig_plt_df = fig_plt_df.drop_duplicates('end', keep='first')
                    fig_plt_df = fig_plt_df.loc[:, ['val']]
                    fig_plt_df = fig_plt_df.rename(columns={"val": fig_plt_view_temp})
                    new_line = graph.Bar(x=fig_plt_df.index.tolist(), y=pd.to_numeric(fig_plt_df[fig_plt_df.columns[0]]), name=str(fig_plt_df.columns[0]))
                    fig_plt.add_trace(new_line)
            
            
            fig_plt.update_layout(xaxis=dict(rangeslider=dict(visible=True)))
            fig_plt.update_layout(legend=dict(yanchor="top", y=1.35, xanchor="left", x=-0.05))
            fig_plt.update_layout(showlegend=True)
            
            fig_plt_1 = plotly.to_html(fig_plt, full_html=False, include_plotlyjs='cdn', config = {'responsive': True, 'displayModeBar': False})
            fig_plt_2 = plotly.to_html(fig_plt, full_html=False, include_plotlyjs='cdn', config = {'responsive': True, 'displayModeBar': False})
            
            raw_data['val'] = raw_data['val'].apply(convert_int)
            raw_data = raw_data.pivot_table(values='val', index=['desc'], columns=['end'], fill_value="0", aggfunc='max')
            raw_data = raw_data[raw_data.columns[::-1]]
            raw_data = raw_data.reset_index()
            BalanceSheet = pd.concat([BalanceSheetA, BalanceSheetL], axis=0)
            BalanceSheet = BalanceSheet.dropna(axis=1)
            BalanceSheet = BalanceSheet[BalanceSheet.columns[::-1]]
            BalanceSheet = BalanceSheet.reset_index()
            BalanceSheet = BalanceSheet.drop(columns=['rnkNum'])

            quick_info = []
            top_two_dates = pd.to_datetime(info_df["end"]).drop_duplicates().nlargest(2)
            tmp_df_val = info_df[pd.to_datetime(info_df["end"]).isin(top_two_dates)]

            date_cols = [col for col in tmp_df_val.columns if col not in ["desc", "rnkNum"]]
            tmp_df_val["desc"] = tmp_df_val["desc"].str.split(".").str[0].str.slice(0, 16)
            tmp_df_val["val"] = tmp_df_val["val"].apply(convert_int)
            df_flat = tmp_df_val.reset_index(drop=True)
            pivoted_df = df_flat.pivot_table(index=["desc", "rnkNum"], columns="end", values="val", aggfunc="first")
            pivoted_df = pivoted_df.sort_values("rnkNum").reset_index(level="rnkNum", drop=True)
            pivoted_df.columns.name = None
            pivoted_df.index.name = None
            col_0 = pd.to_numeric(pivoted_df.iloc[:, 0].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce')
            col_1 = pd.to_numeric(pivoted_df.iloc[:, 1].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce')
            pivoted_df['diff'] = ((col_1 - col_0) / col_0 * 100).map('{:.2f}%'.format)
            quick_info = pivoted_df.to_html(classes="table summary-table")

            context = {'ticker': temptck,
                        'name': tempname,
                        'categories': other_info,
                        'high_low_52w': {'high':round(float(ft_week_h), 2), 
                                        'low':round(float(ft_week_l), 2),
                                        'high_to_close':round(100*((float(ft_week_h)-float(ft_week_close))/float(ft_week_close)), 2),
                                        'open_to_close':round(100*((float(ft_week_open)-float(ft_week_close))/float(ft_week_close)), 2),
                                        'close':round(float(ft_week_close), 2),
                                        'low_to_close':round(100*((float(ft_week_l)-float(ft_week_close))/float(ft_week_close)), 2),
                                        'date':ft_week_date},
                        'incomeStatement': incomeStatement.to_html(classes='table', index=False),
                        'balanceSheet': BalanceSheet.to_html(classes='table', index=False),
                        'cashFlow': CashFlow.to_html(classes='table', index=False),
                        'commonShareouts': NumOfCommonShares.to_html(classes='table', index=False),
                        'perShare': PerShare.to_html(classes='table', index=False),
                        'rawData': raw_data.to_html(classes='table', table_id='raw_data', index=False),
                        'currentPrice': current_market_price.to_html(classes='table'),
                        'price_plt':tmp_p_plt,
                        'links_lst': links_lsts,
                        'quick_info': quick_info,
                        'raw_data_list':raw_data_list,
                        'fig_plt':fig_plt_1,
                        'fig_plt_summary':fig_plt_2,}
            if 'fig_plt_option' in rq:
                context['financials_chart'] = 'yes'
            
        else:
            context = {'ticker': 'Not available',}

        context['links'] = all_links
        context['all_links_data'] = all_links_data

        if "user_prompt" in rq.keys():
            temp_user_prompt = str(rq['user_prompt'])
            temp_choices = rq['choices']

            data_context = {}
            for i in temp_choices:
                if i == "business":
                    temp_data = [x for x in all_links_data if "vs" in x["period_ended"]][0]
                    print(temp_data.keys())
                    data_context['comparisson of year over year 10-K business descriptions'] = {temp_data['period_ended']: temp_data['business_description']}
                elif i == "financials":
                    data_context['summary of financial results'] = quick_info

            temp_model_connection  = model_connection.objects.get(id=5)
            temp_personality = model_personality.objects.get(id=7)
            temp_task = send_task_to_model(promt_message = temp_user_prompt, user_request = request, 
                    personality = temp_personality, run_tempereature=temp_personality.personality_temp, top_p=temp_personality.personality_top_p,
                    chat_summary = data_context, chat_tool = "fast", model_base = temp_model_connection.model_base, #model_con
                    model_name = temp_model_connection.model_name, model_api_key = temp_model_connection.model_api_key,)

            print(temp_task.response)

            context['task_response'] = markdown.markdown(temp_task.response)



        return render(request, 'stock_dashboard/stock_dashboard.html', context)



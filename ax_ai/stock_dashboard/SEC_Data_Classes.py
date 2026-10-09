from synapse.models import *
from synapse.views import get_connection_data, get_local_connection_data, get_connection_data_w_input

import pandas as pd
import numpy as np
import requests, os



class getSECData:
    def __init__(self, ticker):
        self.ticker = ticker
    
    def getCIK(self):
        ticker_cik_list = get_connection_data(connection_functions.objects.get(connection_function_name = "company_tickerscsv"))
        tickers = pd.DataFrame(ticker_cik_list['temp_data'])
        cik = str(tickers[tickers['ticker']==str(self.ticker)]['cik_str'].iloc[0]).zfill(10)

        self.cik = "CIK"+str(cik)
        return self.cik

    def getData(self):
        cik = str(self.getCIK())

        get_cik_data = get_connection_data_w_input(connection_functions.objects.get(connection_function_name = "edgar company facts"), {"CIK":cik})
        get_cik_json = get_cik_data['temp_data']

        self.data = get_cik_json
        return self.data
    
    def getInfo(self):
        cik = str(self.getCIK())

        get_cik_data = get_connection_data_w_input(connection_functions.objects.get(connection_function_name = "edgar company submissions"), {"CIK":cik})
        get_cik_json = get_cik_data['temp_data']

        self.data = get_cik_json

        return get_cik_json



class IncomeStatement:
    def getData(self):
        self.data = pd.DataFrame()
        for row in self.dataframe.columns[self.dataframe.columns.str.contains('.units')]:
            df_tmp = pd.json_normalize(self.dataframe[row][0])
            df_tmp['desc'] = row
            self.data = pd.concat([df_tmp, self.data], axis=0)
        
        self.data = self.data[self.data['form']==self.form]
        return self.data

    def getRevenue(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        revenue = data[data['desc'].str.contains('Revenue')]
        revenue = revenue.sort_values('val').drop_duplicates(subset='end', keep='last')
        revenue = revenue.sort_values('end')
        revenue = revenue[['desc', 'val', 'end']]
        revenue.index = revenue['end']
        revenue['rnk'] = 'Revenue'
        revenue['rnkNum'] = 1
        self.revenue = revenue
        self.latesRevenue = self.revenue[self.revenue.index==max(self.revenue.index)]
        return self.revenue, self.latesRevenue
    
    def getCOGS(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        cogs = data[data['desc'].str.contains('CostOfGoods')]
        cogs = cogs.sort_values('val').drop_duplicates(subset='end', keep='last')
        cogs = cogs.sort_values('end')
        cogs = cogs[['desc', 'val', 'end']]
        cogs.index = cogs['end']
        cogs['rnk'] = 'Cost Of Goods Sold'
        cogs['rnkNum'] = 2
        self.cogs = cogs
        self.latesCogs = self.cogs[self.cogs.index==max(self.cogs.index)]
        return self.cogs, self.latesCogs
  
    def getGrossProfit(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        profit = data[data['desc'].str.contains('Profit')]
        profit = profit.sort_values('val').drop_duplicates(subset='end', keep='last')
        profit = profit.sort_values('end')
        profit = profit[['desc', 'val', 'end']]
        profit.index = profit['end']
        profit['rnk'] = 'Gross Profit'
        profit['rnkNum'] = 3
        self.profit = profit
        self.latestProfit = self.profit[self.profit.index==max(self.profit.index)]
        return self.profit, self.latestProfit
    
    def getSGA(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        if 'Selling' in str(data[data['desc'].str.contains('Admin')]['desc'][0]):
            sga = data[data['desc'].str.contains('Admin')]
            sga = sga.sort_values('val').drop_duplicates(subset='end', keep='last')
            sga  = sga.sort_values('end')
            sga = sga[['desc', 'val', 'end']]
            sga.index = sga['end']
            sga['rnk'] = "SGA"
            sga['rnkNum'] = 4
            self.sga = sga
            self.latestSga = self.sga[self.sga.index==max(self.sga.index)]
            return self.sga, self.latestSga
        else:
            ga = data[data['desc'].str.contains('Admin')]
            ga = ga.sort_values('val').drop_duplicates(subset='end', keep='last')
            ga  = ga.sort_values('end')
            ga = ga[['desc', 'val', 'end']]
            ga.index = ga['end']
            ga['rnk'] = "General and Admin"
            ga['rnkNum'] = 5
            self.ga = ga
            self.latestGa = self.ga[self.ga.index==max(self.ga.index)]

            sga = data[data['desc'].str.contains('Selling')]
            sga = sga.sort_values('val').drop_duplicates(subset='end', keep='last')
            sga  = sga.sort_values('end')
            sga = sga[['desc', 'val', 'end']]
            sga.index = sga['end']
            sga['rnk'] = "Selling and Marketing"
            sga['rnkNum'] = 6
            self.sga = sga
            self.latestSga = self.sga[self.sga.index==max(self.sga.index)]
            return self.sga, self.latestSga, self.ga, self.latestGa

    def getNetIncome(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[self.data['desc'].str.contains('.units')]
        income = data[self.data['desc'].str.contains('NetIncome')]
        income = income.sort_values('val').drop_duplicates(subset='end', keep='last')
        income = income.sort_values('end')
        income = income[['desc', 'val', 'end']]
        income.index = income['end']
        income['rnk'] = "Net Income"
        income['rnkNum'] = 7
        self.income = income
        self.latestIncome = self.income[self.income.index==max(self.income.index)]
        return self.income, self.latestIncome

    def getIncomeStatment(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        self.incomeStatement = pd.DataFrame()
        income = self.getNetIncome()[0]
        revenue = self.getRevenue()[0]
        cogs = self.getCOGS()[0]
        profit = self.getGrossProfit()[0]

        if len(self.getSGA()) > 2:
            selling = self.getSGA()[0]
            ga = self.getSGA()[2]
            self.incomeStatement = self.incomeStatement.append([revenue, cogs, profit, selling, ga, income])
        else:
            sga = self.getSGA()[0]
            self.incomeStatement = self.incomeStatement.append([revenue, cogs, profit, sga, income])
        
        self.incomeStatement = self.incomeStatement.pivot_table(values = 'val', 
                                                                index = ['rnkNum', 'rnk'], 
                                                                columns = self.incomeStatement.index,
                                                                fill_value = 0, 
                                                                aggfunc=np.sum)

        return self.incomeStatement

    def __init__(self, dataframe, form):
        self.dataframe = pd.json_normalize(dataframe['facts']['us-gaap'])
        self.form = str(form)

class BalanceSheet:
    def getData(self):
        self.data = pd.DataFrame()
        for row in self.dataframe.columns[self.dataframe.columns.str.contains('.units')]:
            df_tmp = pd.json_normalize(self.dataframe[row][0])
            df_tmp['desc'] = row
            self.data = pd.concat([df_tmp, self.data], axis=0)
        
        self.data = self.data[self.data['form']==self.form]
        return self.data

    def getCash(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        cash = data[data['desc'].str.contains('CashEquivalent')]
        cash = cash.sort_values('val').drop_duplicates(subset='end', keep='last')
        cash = cash.sort_values('end')
        cash = cash[['desc', 'val', 'end']]
        cash.index = cash['end']
        cash['rnk'] = 'Cash & Equivalents'
        cash['rnkNum'] = 1
        self.cash = cash
        self.latesCash = self.cash[self.cash.index==max(self.cash.index)]
        return self.cash, self.latesCash
    
    def getAccountsRecievable(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        receivables = data[data['desc'].str.contains('Accounts') & data['desc'].str.contains('Receivable')]
        receivables = receivables.sort_values('val').drop_duplicates(subset='end', keep='last')
        receivables = receivables.sort_values('end')
        receivables = receivables[['desc', 'val', 'end']]
        receivables.index = receivables['end']
        receivables['rnk'] = 'Accounts Recivable'
        receivables['rnkNum'] = 2
        self.receivables = receivables
        self.latesReceivables = self.receivables[self.receivables.index==max(self.receivables.index)]
        return self.receivables, self.latesReceivables

    def getInventory(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        inventory = data[data['desc'].str.contains('Inventory')]
        inventory = inventory.sort_values('val').drop_duplicates(subset='end', keep='last')
        inventory = inventory.sort_values('end')
        inventory = inventory[['desc', 'val', 'end']]
        inventory.index = inventory['end']
        inventory['rnk'] = 'Inventory'
        inventory['rnkNum'] = 3
        self.inventory = inventory
        self.latesInventory = self.inventory[self.inventory.index==max(self.inventory.index)]
        return self.inventory, self.latesInventory
    
    def getCurrentAssets(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        current = data[data['desc'].str.contains('AssetsCurrent')]
        current= current.sort_values('val').drop_duplicates(subset='end', keep='last')
        current= current.sort_values('val')
        current= current[['desc', 'val', 'end']]
        current.index = current['end']
        current['rnk'] = "Current Assets"
        current['rnkNum'] = 4
        self.current= current
        self.latestCurrent = self.current[self.current.index==max(self.current.index)]
        return self.current, self.latestCurrent
    
    def getPPE(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        ppe = data[data['desc'].str.contains('PropertyPlantAndEquipmentN')]
        if len(ppe)==0:
            ppe = data[data['desc'].str.contains('PropertyPlantAndEquipmentA')]
        ppe= ppe.sort_values('val').drop_duplicates(subset='end', keep='last')
        ppe= ppe.sort_values('val')
        ppe= ppe[['desc', 'val', 'end']]
        ppe.index = ppe['end']
        ppe['rnk'] = "PP&E"
        ppe['rnkNum'] = 5
        self.ppe= ppe
        self.latestPpe = self.ppe[self.ppe.index==max(self.ppe.index)]
        return self.ppe, self.latestPpe
    
    def getNonCurrentAssets(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        noncurrent = data[data['desc'].str.contains('AssetsNon')]

        noncurrent= noncurrent.sort_values('val').drop_duplicates(subset='end', keep='last')
        noncurrent= noncurrent.sort_values('val')
        noncurrent= noncurrent[['desc', 'val', 'end']]
        noncurrent.index = noncurrent['end']
        noncurrent['rnk'] = "Noncurrent Assets"
        noncurrent['rnkNum'] = 6
        self.noncurrent= noncurrent
        self.latestNoncurrent = self.noncurrent[self.noncurrent.index==max(self.noncurrent.index)]
        return self.noncurrent, self.latestNoncurrent
    
    def getTotalAssets(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        assets = data[data['desc']=='Assets.units.USD']

        assets= assets.sort_values('val').drop_duplicates(subset='end', keep='last')
        assets= assets.sort_values('val')
        assets= assets[['desc', 'val', 'end']]
        assets.index = assets['end']
        assets['rnk'] = "Total Assets"
        assets['rnkNum'] = 7
        self.assets= assets
        self.latestAssets = self.assets[self.assets.index==max(self.assets.index)]
        return self.assets, self.latestAssets
    
    def getDebt(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        debt = data[data['desc'].str.contains('LongTermDebt')]
        debt = debt[~debt['desc'].str.contains('Proceeds')]
        debt = debt[~debt['desc'].str.contains('Repayments')]

        debt= debt.sort_values('val').drop_duplicates(subset='end', keep='last')
        debt= debt.sort_values('val')
        debt= debt[['desc', 'val', 'end']]
        debt.index = debt['end']
        debt['rnk'] = "Long Term Debt"
        debt['rnkNum'] = 9
        self.debt= debt
        self.latestDebt = self.debt[self.debt.index==max(self.debt.index)]
        return self.debt, self.latestDebt
    
    def getCurrentLiabilities(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        currentL = data[data['desc'].str.contains('LiabilitiesC')]

        currentL= currentL.sort_values('val').drop_duplicates(subset='end', keep='last')
        currentL= currentL.sort_values('val')
        currentL= currentL[['desc', 'val', 'end']]
        currentL.index = currentL['end']
        currentL['rnk'] = "Current Liabilities"
        currentL['rnkNum'] = 8
        self.currentL= currentL
        self.latestCurrentL = self.currentL[self.currentL.index==max(self.currentL.index)]
        return self.currentL, self.latestCurrentL
    
    def getTotalLiabilities(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        data = data[data['desc'].str.contains('.units')]
        liabilities = data[data['desc'].str.contains('Liabilities')]
        liabilities = liabilities[~liabilities['desc'].str.contains('Tax')]
        liabilities = liabilities[~liabilities['desc'].str.contains('Increase')]
        liabilities = liabilities[~liabilities['desc'].str.contains('urrent')]
        #liabilities = liabilities[~liabilities['desc'].str.contains('Equity')]
        liabilities = liabilities[~liabilities['desc'].str.contains('Pension')]
        liabilities = liabilities[~liabilities['desc'].str.contains('Other')]

        liabilities= liabilities.sort_values('val').drop_duplicates(subset='end', keep='last')
        liabilities= liabilities.sort_values('val')
        liabilities= liabilities[['desc', 'val', 'end']]
        liabilities.index = liabilities['end']
        liabilities['rnk'] = "Liabilities"
        liabilities['rnkNum'] = 10
        self.liabilities= liabilities
        self.latestLiabilities = self.liabilities[self.liabilities.index==max(self.liabilities.index)]
        return self.liabilities, self.latestLiabilities

    def getBalanceSheetAssets(self):
        self.getData()
        BalanceSheetA = pd.DataFrame()
        cash = self.getCash()[0]
        accountsRec = self.getAccountsRecievable()[0]
        inventory = self.getInventory()[0]
        currentAssets = self.getCurrentAssets()[0]
        ppe = self.getPPE()[0]
        nonCurrent = self.getNonCurrentAssets()[0]
        assets = self.getTotalAssets()[0]
        BalanceSheetA = pd.concat([cash, accountsRec, inventory, currentAssets, ppe, nonCurrent, assets], axis=0)
        BalanceSheetA = BalanceSheetA.pivot_table(values = 'val', index = ['rnkNum', 'rnk'], columns = BalanceSheetA.index, fill_value = 0, aggfunc=np.sum)
        self.BalanceSheetA = BalanceSheetA
        return self.BalanceSheetA
    
    def getBalanceSheetLiabilities(self):
        self.getData()
        BalanceSheetL = pd.DataFrame()
        currentL = self.getCurrentLiabilities()[0]
        debt = self.getDebt()[0]
        liabilities = self.getTotalLiabilities()[0]
        BalanceSheetL = pd.concat([currentL, debt, liabilities], axis=0)
        BalanceSheetL = BalanceSheetL.pivot_table(values = 'val', index = ['rnkNum', 'rnk'], columns = BalanceSheetL.index, fill_value = 0, aggfunc=np.sum)
        self.BalanceSheetL = BalanceSheetL
        return self.BalanceSheetL

    def __init__(self, dataframe, form):
        self.dataframe = pd.json_normalize(dataframe['facts']['us-gaap'])
        self.form = str(form)

class CashFlow:
    def getData(self):
        self.data = pd.DataFrame()
        for row in self.dataframe.columns[self.dataframe.columns.str.contains('.units')]:
            df_tmp = pd.json_normalize(self.dataframe[row][0])
            df_tmp['desc'] = row
            self.data = pd.concat([df_tmp, self.data], axis=0)
        
        self.data = self.data[self.data['form']==self.form]
        return self.data
    
    def getNetCashFlow(self):
        if hasattr(self, 'data'):
            data = self.data
        else:
            data = self.getData()
        
        data = data[data['desc'].str.contains('.units')]
        cash = data[data['desc'].str.contains('CashEquivalent')]
        cash = cash.sort_values('val').drop_duplicates(subset='end', keep='last')
        cash = cash.sort_values('end')
        cash = cash[['desc', 'val', 'end']]
        cash.index = cash['end']
        cash['rnk'] = 'Cash & Equivalents'
        cash['rnkNum'] = 1

        nt_tmp = data[data['desc'].str.contains('NetCash')]

        nt_o = nt_tmp[nt_tmp['desc'].str.contains('Operating')]
        nt_o = nt_o.sort_values('val').drop_duplicates(subset='end', keep='last')
        nt_o = nt_o.sort_values('end')
        nt_o = nt_o[['desc', 'val', 'end']]
        nt_o.index = nt_o['end']
        nt_o['rnk'] = 'Net Cash from Operating Activities'
        nt_o['rnkNum'] = 2

        nt_f = nt_tmp[nt_tmp['desc'].str.contains('Financing')]
        nt_f = nt_f.sort_values('val').drop_duplicates(subset='end', keep='last')
        nt_f = nt_f.sort_values('end')
        nt_f = nt_f[['desc', 'val', 'end']]
        nt_f.index = nt_f['end']
        nt_f['rnk'] = 'Net Cash from Financing Activities'
        nt_f['rnkNum'] = 3

        nt_i = nt_tmp[nt_tmp['desc'].str.contains('Investing')]
        nt_i = nt_i.sort_values('val').drop_duplicates(subset='end', keep='last')
        nt_i = nt_i.sort_values('end')
        nt_i = nt_i[['desc', 'val', 'end']]
        nt_i.index = nt_i['end']
        nt_i['rnk'] = 'Net Cash from Investing Activities'
        nt_i['rnkNum'] = 4

        cashflow = pd.concat([cash, nt_f, nt_i, nt_o], axis=0)
        cashflow = cashflow.pivot_table(values = 'val', index = ['rnkNum', 'rnk'], columns = cashflow.index, fill_value = 0, aggfunc=np.sum)

        return cashflow
    
    def __init__(self, dataframe, form):
        self.dataframe = pd.json_normalize(dataframe['facts']['us-gaap'])
        self.form = str(form)

class StockInfo:
    def getData(self):
        self.data = pd.DataFrame()
        for row in self.dataframe.columns[self.dataframe.columns.str.contains('.units')]:
            df_tmp = pd.json_normalize(self.dataframe[row][0])
            df_tmp['desc'] = row
            self.data = pd.concat([df_tmp, self.data], axis=0)
        
        self.data = self.data[self.data['fy']==self.year]
        self.date = max(self.data['filed'])
        self.data = self.data[self.data['filed']==self.date]

        return self.data
    
    def getPublicFloat(self):
        data = self.getData()
        PublicFloat = data[data['desc'].str.contains('PublicFloat')]
        PublicFloat = PublicFloat[PublicFloat['val']==max(PublicFloat['val'])]
        return PublicFloat
    
    def getNumOfCommonShares(self):
        data = self.getData()
        NumOfCommonShares = data[data['desc'].str.contains('.shares')]
        NumOfCommonShares = NumOfCommonShares[NumOfCommonShares['val']==max(NumOfCommonShares['val'])]
        return NumOfCommonShares

    def __init__(self, dataframe, year):
        self.year = year
        self.dataframe = pd.json_normalize(dataframe['facts']['dei'])
        self.data = self.getData()
        


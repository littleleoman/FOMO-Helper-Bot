import re
from decimal import Decimal

def feeCalc(sale_price):
    # List of websites 
    sites = []
    
    # Simple check for a monetary value
    if re.match('^\d+(\.\d*)*$', sale_price) == None:
        return("ERROR")
    else:
        price = Decimal(sale_price)
        price = round(price, 2)
        
        # Tuple format
        #    - site title
        #    - fee percentage
        #    - fixed fee (0 if none)
        ebay = ('eBay', 0.129, 0.00)
        grailed = ('Grailed', 0.089, 0.30)
        paypal = ('PayPal', 0.029, 0.30)
        goat = ('Goat', 0.095, 5.00)
        stockx = ('StockX', 0.120, 0.00)
        shopify = ('Basic Shopify', 0.029, 0.30)
        sites.append(ebay)
        sites.append(grailed)
        sites.append(paypal)
        sites.append(goat)
        sites.append(stockx)
        sites.append(shopify)
        
        websites = ''
        fees = ''
        profits = ''
        # For each site, format information for display on Discord
        for i in sites:
            websites += i[0] + '\n'
            fee = round(price * Decimal(i[1]), 2)
            fees += '$' + str(round(fee + Decimal(i[2]), 2)) + '\n'
            after_fee = round(price - fee - Decimal(i[2]), 2)
            profits += '$' + str(after_fee) + '\n'
        return{
            'websites':websites,
            'fees':fees,
            'profits':profits
        }
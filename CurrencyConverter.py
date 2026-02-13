import requests
import os

class ConversionStrategy:
    def convert(self, amount, from_unit, to_unit):
        raise NotImplementedError("Subclasses must implement convert()")

class CurrencyConverter(ConversionStrategy):
    def __init__(self, api_key):
        # Your actual key stays here
        self.api_key = "3c22d36402-3f4de276ae-taetcf" 
        self.base_url = "https://api.fastforex.io/convert"

    def convert(self, amount, from_curr, to_curr):
        params = {
            "from": from_curr,
            "to": to_curr,
            "amount": amount,
            "api_key": self.api_key
        }
        response = requests.get(self.base_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return data['result'][to_curr]
        else:
            return f"Error: {response.status_code}"

if __name__ == "__main__":
    my_converter = CurrencyConverter("YOUR_API_KEY")

    print("--- Real-Time Currency Converter ---")
    
    # 1. Get the source currency (e.g., USD)
    base = input("Enter the currency you HAVE (e.g., USD): ").upper()
    
    # 2. Get the target currency (e.g., EUR)
    target = input("Enter the currency you WANT (e.g., EUR): ").upper()
    
    # 3. Get the amount and convert it to a number
    try:
        amount_to_convert = float(input(f"How much {base} do you want to convert? "))
        
        # 4. Run the conversion
        result = my_converter.convert(amount_to_convert, base, target)
        
        print("-" * 30)
        print(f"{amount_to_convert} {base} is equal to {result} {target}")
        print("-" * 30)
        
    except ValueError:
        print("Invalid amount! Please enter a number (e.g., 100 or 50.50).")
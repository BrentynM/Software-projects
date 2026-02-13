import streamlit as st
import requests

# 1. Your existing logic
class CurrencyConverter:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.fastforex.io/convert"

    def convert(self, amount, from_curr, to_curr):
        params = {
            "from": from_curr,
            "to": to_curr,
            "amount": amount,
            "api_key": self.api_key
        }
        try:
            response = requests.get(self.base_url, params=params)
            if response.status_code == 200:
                return response.json()['result'][to_curr]
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"Connection Error: {e}"

# 2. The Website Interface
st.set_page_config(page_title="Global Currency Converter", page_icon="💰")

st.title("🌍 Currency Converter")
st.markdown("Convert between fiat and crypto using real-time rates from fastFOREX.")

# Sidebar for the API Key (keeps the UI clean)
api_key = st.sidebar.text_input("Enter fastFOREX API Key", type="password", value="3c22d36402-3f4de276ae-taetcf")

col1, col2 = st.columns(2)

with col1:
    amount = st.number_input("Amount to convert", min_value=0.0, value=100.0)
    from_curr = st.text_input("From (e.g., USD)", value="USD").upper()

with col2:
    to_curr = st.text_input("To (e.g., EUR)", value="EUR").upper()
    
if st.button("Convert Now"):
    if not api_key:
        st.error("Please enter an API Key in the sidebar!")
    else:
        converter = CurrencyConverter(api_key)
        result = converter.convert(amount, from_curr, to_curr)
        
        if isinstance(result, float):
            st.success(f"### {amount} {from_curr} = {result:,.2f} {to_curr}")
        else:
            st.error(result)
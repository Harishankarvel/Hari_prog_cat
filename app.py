import streamlit as st
import requests
import openai

# ---- Configuration ----
openai.api_key = "YOUR_OPENAI_API_KEY"
weather_api_key = "YOUR_OPENWEATHER_API_KEY"

st.set_page_config(page_title="🌦️ WeatherBot", layout="centered")
st.title("🌤️ Weather Dashboard with Chatbot")

# ---- Get weather data from OpenWeatherMap ----
def get_weather(city):
    base_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api_key}&units=metric"
    response = requests.get(base_url)
    if response.status_code == 200:
        data = response.json()
        main = data["main"]
        weather = data["weather"][0]
        return {
            "city": city.title(),
            "temperature": main["temp"],
            "humidity": main["humidity"],
            "condition": weather["description"].title()
        }
    else:
        return None

# ---- Chatbot to respond using OpenAI ----
def ask_chatbot(prompt):
    messages = [
        {"role": "system", "content": "You are a helpful weather assistant."},
        {"role": "user", "content": prompt}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return f"Error: {e}"

# ---- UI Section ----
tab1, tab2 = st.tabs(["📍 Weather Info", "💬 Chatbot"])

with tab1:
    city = st.text_input("Enter City Name", "Chennai")
    if st.button("Get Weather"):
        result = get_weather(city)
        if result:
            st.metric("City", result["city"])
            st.metric("Temperature (°C)", result["temperature"])
            st.metric("Humidity (%)", result["humidity"])
            st.info(f"Condition: {result['condition']}")
        else:
            st.error("City not found or error fetching data.")

with tab2:
    st.subheader("Ask about weather ✨")
    user_query = st.text_input("Type your question...")
    if st.button("Ask"):
        if user_query:
            response = ask_chatbot(user_query)
            st.success(response)

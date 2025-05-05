from flask import Flask, render_template, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import json
import re
from datetime import datetime

app = Flask(__name__)

tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")

with open("data/products.json", "r") as f:
    product_data = json.load(f)

user_histories = {}
user_carts = {}

def preprocess_text(text):
    return re.sub(r"[^a-zA-Z0-9 ]", "", text.lower())

def get_ai_reply(user_input, user_id="user"):
    if user_id not in user_histories:
        user_histories[user_id] = None

    input_ids = tokenizer.encode(user_input + tokenizer.eos_token, return_tensors='pt')
    chat_history = user_histories[user_id]

    bot_input_ids = torch.cat([chat_history, input_ids], dim=-1) if chat_history is not None else input_ids
    output = model.generate(bot_input_ids, max_length=1000, pad_token_id=tokenizer.eos_token_id)

    user_histories[user_id] = output
    response = tokenizer.decode(output[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
    return response

def recommend_products(user_id):
    cart_items = user_carts.get(user_id, [])
    if not cart_items:
        return "You have no items in your cart yet. How about exploring some trending products?"

    recommendations = []
    for item in cart_items:
        for product in product_data:
            if item['category'] == product['category'] and item['name'] != product['name']:
                recommendations.append(product)
    
    if recommendations:
        return f"Here are some products you might like: {', '.join([p['name'] for p in recommendations])}"
    return "We couldn't find any personalized recommendations right now."

def match_product_keywords(message):
    message = preprocess_text(message)
    matched = []
    for product in product_data:
        for keyword in product["keywords"]:
            if keyword in message:
                matched.append(product)
                break
    return matched

def time_based_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning! How can I help you today?"
    elif hour < 18:
        return "Good afternoon! What are you looking for today?"
    else:
        return "Good evening! Need help finding the right product?"

def add_to_cart(user_id, product_name):
    if user_id not in user_carts:
        user_carts[user_id] = []
    for product in product_data:
        if preprocess_text(product["name"]) in preprocess_text(product_name):
            user_carts[user_id].append(product)
            return f"Added {product['name']} to your cart."
    return "Sorry, I couldn't find that product to add."

def remove_from_cart(user_id, product_name):
    if user_id in user_carts:
        for item in list(user_carts[user_id]):
            if preprocess_text(item["name"]) in preprocess_text(product_name):
                user_carts[user_id].remove(item)
                return f"Removed {item['name']} from your cart."
    return f"{product_name} is not in your cart."

def show_cart(user_id):
    cart_items = user_carts.get(user_id, [])
    if cart_items:
        seen = set()
        unique_cart = []
        for item in cart_items:
            identifier = item['name']
            if identifier not in seen:
                seen.add(identifier)
                unique_cart.append(item)
        lines = [f"{item['name']} - {item['price']}" for item in unique_cart]
        return "Your cart contains:\n" + "\n".join(lines)
    return "Your cart is empty."

def handle_cart_commands(message, user_id):
    message = preprocess_text(message)
    if "show cart" in message or "view cart" in message:
        return show_cart(user_id)
    if "add" in message:
        for product in product_data:
            if any(keyword in message for keyword in product["keywords"]):
                return add_to_cart(user_id, product["name"])
    if "remove" in message:
        for product in product_data:
            if any(keyword in message for keyword in product["keywords"]):
                return remove_from_cart(user_id, product["name"])
    return None

@app.route('/')
def home():
    return render_template("chat.html")

@app.route('/chat', methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    user_id = data.get("user_id", "default_user")

    if user_message.strip().lower() in ["hi", "hello"]:
        bot_reply = time_based_greeting()
    else:
        if "recommend" in user_message.lower() or "suggest" in user_message.lower():
            bot_reply=recommend_products(user_id)
        else:
            cart_response = handle_cart_commands(user_message, user_id)
            if cart_response:
                bot_reply = cart_response
            else:
                matched_products = match_product_keywords(user_message)
                if matched_products:
                    product = matched_products[0]
                    bot_reply = f"{product['name']} - {product['description']}. Price: {product.get('price', 'INR N/A')}"
                else:
                    bot_reply = get_ai_reply(user_message, user_id)

    return jsonify({"reply": bot_reply})

if __name__ == '__main__':
    app.run(debug=True)

#include <WiFi.h>
#include <WebServer.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>


const char* ssid = "HSV's Realme";
const char* password = "hari2408";


WebServer server(80);


#define SS_PIN 4
#define RST_PIN 15
MFRC522 mfrc522(SS_PIN, RST_PIN);


#define ADD_LED 25
#define REMOVE_LED 14
#define BUZZER 26
#define CHECKOUT_BUTTON 27
#define REMOVE_SWITCH_PIN 32

// LCD Display
#define LCD_ADDR 0x27
#define LCD_COLS 16
#define LCD_ROWS 2
LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);

// ---------- CART & BILLING SYSTEM ----------
#define MAX_UNIQUE_ITEMS 30
#define GST_RATE 0.02      

// Structure for a single item in the cart
struct CartItem {
  String name;
  int price;
  int quantity;
};

CartItem cart[MAX_UNIQUE_ITEMS]; // The array for our cart
int uniqueItemCount = 0;         // Number of unique items currently in cart
int subTotalPrice = 0;           // Total price BEFORE GST
int totalItemCount = 0;          // Total number of all items

// ---------- GLOBAL VARIABLES ----------
MFRC522::MIFARE_Key key;
bool lastButtonState = HIGH; // For detecting button press edge

// =================================================================
//                         CART HELPER FUNCTIONS
// =================================================================

/**
 * Finds an item in the cart by its product name.
 * @param productName The name of the product to find.
 * @return The index of the item if found, otherwise -1.
 */
int findItemInCart(String productName) {
  for (int i = 0; i < uniqueItemCount; i++) {
    if (cart[i].name == productName) {
      return i; // Found it
    }
  }
  return -1; // Not found
}

/**
 * Clears the entire cart and resets all totals to zero.
 */
void clearCart() {
  subTotalPrice = 0;
  totalItemCount = 0;
  uniqueItemCount = 0;
  // No need to clear array data; setting uniqueItemCount to 0 effectively "empties" it.
}

/**
 * Adds a given product to the cart.
 * If the item already exists, its quantity is incremented.
 * If it's a new item, it's added to the cart.
 * @param product The name of the product.
 * @param price The price of the product.
 */
void addItemToCart(String product, int price) {
  int index = findItemInCart(product);

  if (index != -1) {
    // Item already in cart, just increment quantity
    cart[index].quantity++;
  } else if (uniqueItemCount < MAX_UNIQUE_ITEMS) {
    // New item, add it to the cart
    cart[uniqueItemCount].name = product;
    cart[uniqueItemCount].price = price;
    cart[uniqueItemCount].quantity = 1;
    uniqueItemCount++;
  } else {
    // Cart is full of unique items
    Serial.println("Cart is full of unique items! Cannot add more.");
    // You could add an error signal here (e.g., blink red LED)
  }
  
  // Update totals
  subTotalPrice += price;
  totalItemCount++;
}

/**
 * Removes one instance of a product from the cart.
 * Decrements the quantity and updates totals.
 * @param product The name of the product.
 * @param price The price of the product.
 */
void removeItemFromCart(String product, int price) {
  int index = findItemInCart(product);

  if (index != -1 && cart[index].quantity > 0) {
    // Item is in cart and has quantity > 0
    cart[index].quantity--;
    subTotalPrice -= price;
    totalItemCount--;
  } else {
    // Item not in cart or quantity is already 0
    Serial.println("Cannot remove item, not in cart or qty=0");
  }
}

// =================================================================
//                   HTML GENERATION FUNCTIONS (NEW)
// =================================================================

/**
 * Builds the HTML for the current bill (table and totals).
 * This is used for the AJAX refresh.
 * @return A String containing the HTML for the bill section.
 */
String buildBillHtml() {
  String html = "<h2>Current Bill</h2>";
  
  // Build the item table
  html += "<table><tr><th>Product</th><th>Qty</th><th>Price</th><th>Total</th></tr>";
  if (uniqueItemCount == 0) {
    html += "<tr><td colspan='4'>Cart is empty. Please scan an item.</td></tr>";
  } else {
    bool itemsInCart = false;
    for (int i = 0; i < uniqueItemCount; i++) {
      if (cart[i].quantity > 0) { // Only show items that are actually in the cart
        itemsInCart = true;
        int itemTotal = cart[i].price * cart[i].quantity;
        html += "<tr>";
        html += "<td>" + cart[i].name + "</td>";
        html += "<td>" + String(cart[i].quantity) + "</td>";
        html += "<td>" + String(cart[i].price) + " Rs</td>";
        html += "<td>" + String(itemTotal) + " Rs</td>";
        html += "</tr>";
      }
    }
    if (!itemsInCart) {
        html += "<tr><td colspan='4'>Cart is empty. Please scan an item.</td></tr>";
    }
  }
  html += "</table>";

  // Calculate totals
  float gst = subTotalPrice * GST_RATE;
  float grandTotal = subTotalPrice + gst;

  // Build the totals section
  html += "<div id='totals'>";
  html += "<h3>Subtotal: " + String(subTotalPrice) + " Rs</h3>";
  html += "<h3>GST (2%): " + String(gst, 2) + " Rs</h3>"; // Show 2 decimal places
  html += "<h2>Grand Total: " + String(grandTotal, 2) + " Rs</h2>";
  html += "</div>";

  return html;
}


/**
 * Builds the main, full HTML page with CSS and JavaScript.
 * @return A String containing the complete HTML page.
 */
String buildMainPageHtml() {
  String html = "<!DOCTYPE html><html><head><title>SHOP CART-Checkout Bill</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>"; // For mobile view
  html += "<style>"
          "body{background:#f0f4f8; font-family:Arial, sans-serif; text-align:center; margin:0; padding:20px;}"
          "h1{color:#0b3d91;} h1 span{font-size:1.5em; vertical-align:middle;}"
          "#bill-container{border:1px solid #ddd; padding: 20px; margin: 20px auto; max-width: 600px; border-radius:12px; background:white; box-shadow:0 4px 8px rgba(0,0,0,0.1);}"
          "table{width:100%; margin:20px 0; border-collapse:collapse;}"
          "th,td{border:1px solid #e0e0e0; padding:10px; text-align:left;}"
          "th{background:#f7f7f7;}"
          "td:nth-child(2),td:nth-child(3),td:nth-child(4){text-align:right;}"
          "#totals{text-align:right; max-width:300px; margin-left:auto; border-top:2px solid #333; padding-top:10px;}"
          "h2,h3{margin:5px 0; color:#333;}"
          "button{background:#d9534f; color:white; font-size:16px; padding:12px 25px; margin-top:20px; border:none; border-radius:8px; cursor:pointer; transition: background 0.3s;}"
          "button:hover{background:#c9302c;}"
          "#message{color:green; font-weight:bold; height:20px; margin-top:10px;}"
          "</style>";
  html += "<script>"
          "function refreshStatus(){"
            "fetch('/status').then(response=>response.text()).then(data=>{"
              "document.getElementById('bill-container').innerHTML = data;"
            "});"
          "}"
          "function doCheckout(){"
            "fetch('/checkout', { method: 'POST' }).then(response=>{"
              "if(response.ok){"
                "document.getElementById('message').innerText = 'Checkout Successful! Resetting...';"
                "setTimeout(() => { document.getElementById('message').innerText = ''; refreshStatus(); }, 2000);"
              "}"
            "});"
          "}"
          "setInterval(refreshStatus, 1500);" // Refresh every 1.5 seconds
          "</script>";
  html += "</head><body>";
  // --- NAME CHANGE HERE & SYMBOL REMOVED ---
  html += "<h1>Shopping Cart Billing System</h1>";
  html += "<div id='bill-container'>Loading bill...</div>";
  html += "<button onclick='doCheckout()'>Checkout & Reset</button>";
  html += "<div id='message'></div>";
  html += "</body></html>";
  return html;
}

// =================================================================
//                       WEB SERVER HANDLERS
// =================================================================

// Serves the main HTML page
void handleRoot() {
  server.send(200, "text/html", buildMainPageHtml());
}

// Sends the current cart status (called by AJAX)
void handleStatus() {
  server.send(200, "text/html", buildBillHtml());
}

// Handles the checkout request from the web page
void handleCheckout() {
  performCheckout("Web Interface");
  server.send(200, "text/plain", "OK"); // Send simple response
}

// =================================================================
//                       CORE LOGIC FUNCTIONS
// =================================================================

/**
 * Updates the LCD with a primary line and a temporary message.
 * @param message The message to show on the second line.
 * @param delayMs The duration to show the message before reverting.
 */
void updateLcdDisplay(String message, int delayMs) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Total: " + String(subTotalPrice) + " Rs"); 
  lcd.setCursor(0, 1);
  lcd.print(message);
  if (delayMs > 0) {
    delay(delayMs);
    // Revert to default message after the delay
    lcd.setCursor(0, 1);
    lcd.print("Scan an item... ");
  }
}

/**
 * Reads data from a specified block on the RFID card.
 * @param blockNum The block number to read from.
 * @return The content read from the card as a String.
 */
String readBlock(int blockNum) {
  byte buffer[18];
  byte bufferLen = sizeof(buffer);
  
  MFRC522::StatusCode status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockNum, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Auth failed: "); Serial.println(mfrc522.GetStatusCodeName(status));
    return "Auth Error";
  }

  status = mfrc522.MIFARE_Read(blockNum, buffer, &bufferLen);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Read failed: "); Serial.println(mfrc522.GetStatusCodeName(status));
    return "Read Error";
  }

  String content = "";
  for (int i = 0; i < 16; i++) {
    if (isprint(buffer[i])) { // Only add printable characters
      content += char(buffer[i]);
    }
  }
  content.trim();
  return content;
}

/**
 * Extracts the integer number from a price string (e.g., "40Rs" -> 40).
 * @param priceStr The string containing the price.
 * @return The extracted price as an integer.
 */
int extractPrice(String priceStr) {
  String numStr = "";
  for (int i = 0; i < priceStr.length(); i++) {
    if (isDigit(priceStr[i])) {
      numStr += priceStr[i];
    }
  }
  return numStr.toInt();
}

/**
 * NEW: Centralized function to handle all checkout logic.
 * This is called by both the physical button and the web interface.
 * @param source A string indicating where the checkout was triggered from (for logging).
 */
void performCheckout(String source) {
  Serial.println("\n-----------------");
  Serial.println("=== CHECKOUT from " + source + " ===");
  Serial.print("Final Subtotal = "); Serial.print(subTotalPrice); Serial.println(" Rs");
  
  float grandTotal = subTotalPrice + (subTotalPrice * GST_RATE);
  Serial.print("Final Grand Total = "); Serial.print(grandTotal, 2); Serial.println(" Rs");
  Serial.println("-----------------");

  // Display final total on LCD
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Final Total:");
  lcd.setCursor(0, 1);
  lcd.print(String(grandTotal, 2) + " Rs");
  delay(3000);

  // Display "SCAN TO PAY" message
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("****************");
  lcd.setCursor(0, 1);
  lcd.print("  SCAN TO PAY   ");
  
  // Signal checkout with buzzer and LED
  digitalWrite(REMOVE_LED, HIGH);
  digitalWrite(BUZZER, HIGH);
  delay(500);
  digitalWrite(REMOVE_LED, LOW);
  digitalWrite(BUZZER, LOW);
  delay(4000); // Wait for payment

  clearCart(); // Reset cart and totals
  updateLcdDisplay("Cart is Empty", 2000); // Reset LCD and show message
}


// =================================================================
//                         SETUP FUNCTION
// =================================================================
void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();

  // Initialize LCD
  lcd.init();
  lcd.backlight();

  // Prepare the default key for MIFARE cards
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

  // Setup pin modes
  pinMode(ADD_LED, OUTPUT);
  pinMode(REMOVE_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  pinMode(CHECKOUT_BUTTON, INPUT_PULLUP);
  pinMode(REMOVE_SWITCH_PIN, INPUT_PULLUP);

  Serial.println("\n===============================");
  // --- NAME CHANGE HERE ---
  Serial.println("  RFID Shopping Cart Billing System");
  Serial.println("===============================");

  // --- WiFi & Web Server Setup ---
  lcd.setCursor(0, 0);
  lcd.print("Connecting WiFi...");
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.println("IP Address: " + WiFi.localIP().toString());
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("IP Address:");
  lcd.setCursor(0, 1);
  lcd.print(WiFi.localIP().toString());
  delay(2500);
  
  // --- Original Startup ---
  // --- NAME CHANGE HERE ---
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Shopping Cart");
  lcd.setCursor(0, 1);
  lcd.print("Billing System");
  delay(2000);
  updateLcdDisplay("Scan an item...", 0);

  // --- Start Web Server Handlers ---
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/checkout", HTTP_POST, handleCheckout);
  server.begin();
  Serial.println("Web server started. Open the IP address in your browser.");
}

// =================================================================
//                           MAIN LOOP
// =================================================================
void loop() {
  server.handleClient(); // Handle incoming web requests

  // --- PHYSICAL CHECKOUT BUTTON ---
  bool buttonState = digitalRead(CHECKOUT_BUTTON);
  if (lastButtonState == HIGH && buttonState == LOW) {
    delay(50); // Simple debounce
    if (digitalRead(CHECKOUT_BUTTON) == LOW) {
        performCheckout("Physical Button");
    }
  }
  lastButtonState = buttonState;

  // --- RFID CARD DETECTION ---
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    return; // No new card, exit loop early
  }

  // A card has been presented. Decide whether to add or remove.
  if (digitalRead(REMOVE_SWITCH_PIN) == LOW) {
    // --- REMOVE ITEM MODE ---
    Serial.println("\n**Card Detected for REMOVAL**");
    digitalWrite(REMOVE_LED, HIGH);
    digitalWrite(BUZZER, HIGH);

    String product = readBlock(4);
    String priceStr = readBlock(5);
    int price = extractPrice(priceStr);

    if(price > 0) {
      removeItemFromCart(product, price);
      Serial.print("Item Removed: "); Serial.println(product);
      Serial.print("New Subtotal: "); Serial.println(subTotalPrice);
      updateLcdDisplay("Item Removed!", 1500);
    } else {
      Serial.println("Error reading card for removal.");
      updateLcdDisplay("Read Error!", 1500);
    }

    digitalWrite(REMOVE_LED, LOW);
    digitalWrite(BUZZER, LOW);

  } else {
    // --- ADD ITEM MODE (Default) ---
    Serial.println("\n**Card Detected for ADDITION**");
    digitalWrite(ADD_LED, HIGH);
    digitalWrite(BUZZER, HIGH);

    String product = readBlock(4);
    String priceStr = readBlock(5);
    int price = extractPrice(priceStr);

    if(price > 0) {
      addItemToCart(product, price);
      Serial.print("Product: "); Serial.println(product);
      Serial.print("Price: "); Serial.println(priceStr);
      Serial.print("New Subtotal: "); Serial.println(subTotalPrice);
      updateLcdDisplay("Item Added!", 1500);
    } else {
      Serial.println("Error reading card for addition.");
      updateLcdDisplay("Read Error!", 1500);
    }

    digitalWrite(ADD_LED, LOW);
    digitalWrite(BUZZER, LOW);
  }

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}






from machine import ADC, Pin
from time import sleep_us, ticks_us, ticks_diff
import network
import time
import uasyncio as asyncio
from microdot import Microdot
from _thread import start_new_thread, allocate_lock
import gc
import _thread

# Timing thresholds (in microseconds) for 200ms dot duration
DOT = 100_000  # 200 ms
DASH_DURATION = 3.15*DOT  # 600 ms
SYMBOL_GAP = DOT  # 200 ms
CHARACTER_GAP = 3*DOT  # 600 ms
WORD_GAP = 7*DOT  # 1400 ms
DOT_DURATION = 1.15 * DOT

# Configure ADC on pin 4
adc = ADC(Pin(4))
adc.atten(ADC.ATTN_0DB)  # Allows reading up to ~3.6V
adc.width(ADC.WIDTH_12BIT)  # 12-bit resolution (0-4095)

# Globals for Morse code and decoded message
morse_code = ""
decoded_message = ""
message_lock = allocate_lock()  # Lock for thread-safe access

# Morse code dictionary
MORSE_CODE_DICT = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
    "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K", ".-..": "L",
    "--": "M", "-.": "N", "---": "O", ".--.": "P", "--.-": "Q", ".-.": "R",
    "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
    "-.--": "Y", "--..": "Z", "-----": "0", ".----": "1", "..---": "2",
    "...--": "3", "....-": "4", ".....": "5", "-....": "6", "--...": "7",
    "---..": "8", "----.": "9"
}

HIGH_THRESHOLD = 2400  # 2.4V in ADC units (~2730 for 3.3V reference)
LOW_THRESHOLD = 500    # 0.5V in ADC units (~570 for 3.3V reference)

HIGH_THRESHOLD = 2400  # 2.4V in ADC units (~2730 for 3.3V reference)
LOW_THRESHOLD = 500    # 0.5V in ADC units (~570 for 3.3V reference)

# Initialize web server
app = Microdot()

def read_signal():
    """Read ADC value and return high/low based on thresholds."""
    adc_value = adc.read()
    if adc_value > HIGH_THRESHOLD:
        return 1  # High signal
    elif adc_value < LOW_THRESHOLD:
        return 0  # Low signal
    return -1  # Ignore noisy readings

def decode_morse(signal_sequence):
    """Decode a sequence of Morse code into text."""
    words = signal_sequence.split("   ")  # Split by word gap
    decoded_text = []  # Initialize an empty list to store decoded words
    for word in words:
        symbols = word.split(" ")  # Split by character gap
        decoded_word = ''.join([MORSE_CODE_DICT.get(symbol, "?") for symbol in symbols])
        decoded_text.append(decoded_word)
    return ' '.join(decoded_text)  # Join decoded words with spaces

def setup_ap():
    """Set up the ESP32 in Access Point mode."""
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="morse_code_reader", password="ece_6440", authmode=network.AUTH_WPA2_PSK)
    while not ap.active():
        time.sleep(0.1)
    print(f"Access Point ready, IP: {ap.ifconfig()[0]}")

@app.route("/")
def index(request):
    """Serve the index HTML file."""
    try:
        with open("index.html", "r") as file:
            html_content = file.read()
        print("Serving index.html")
        return html_content, 200, {"Content-Type": "text/html"}
    except OSError as e:
        print(f"Error serving index.html: {e}")
        return "Error: index.html not found", 404

@app.route("/message")
def message(request):
    """Return the current Morse code and decoded message."""
    with message_lock:
        return {
            "morse": morse_code,
            "message": decoded_message
        }
def run_web_server():
    """Run the Microdot web server."""
    print("Starting web server...")
    try:
        app.run(port=5000, debug=True)
    except Exception as e:
        print(f"Web server error: {e}")

def start_server_thread():
    """Start the web server in a separate thread."""
    print("Starting server thread...")
    try:
        _thread.start_new_thread(run_web_server, ())
    except Exception as e:
        print(f"Error starting server thread: {e}")

async def detect_morse():
    """Listen for and decode Morse code signals."""
    global morse_code, decoded_message
    print("Listening for Morse code...")
    signal_sequence = ""
    last_signal = 0
    last_change = ticks_us()  # Microsecond precision
    
    while True:
        signal = read_signal()
        now = ticks_us()

        if signal != last_signal:  # Signal changed
            duration = ticks_diff(now, last_change)
            last_change = now
            
            if last_signal == 1:  # High signal ended
                if duration <= DOT_DURATION:
                    signal_sequence += "."
                elif duration <= DASH_DURATION:
                    signal_sequence += "-"
            
            elif last_signal == 0:  # Low signal ended
                if duration > WORD_GAP:
                    signal_sequence += "   "  # Word gap
                elif duration > CHARACTER_GAP:
                    signal_sequence += " "  # Character gap
        
        last_signal = signal

        # Decode the message when idle
        if ticks_diff(ticks_us(), last_change) > 2_000_000 and signal_sequence:
            with message_lock:
                morse_code = signal_sequence.strip()
                decoded_message = decode_morse(morse_code)
            print(f"Raw Morse: {morse_code}")
            print(f"Decoded Message: {decoded_message}")
            signal_sequence = ""  # Reset for next message
        sleep_us(1)
    
async def main():
    """Main entry point for the program."""
    print("Starting main program")

    # Set up Access Point
    setup_ap()

    # Start the web server in a separate thread
    start_server_thread()

    # Start Morse code detection
    print("Starting detect_morse task")
    await detect_morse()

# Run the asyncio event loop
asyncio.run(main())


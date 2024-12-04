from machine import Pin
import network
import time
import uasyncio as asyncio
from microdot import Microdot, send_file
from _thread import start_new_thread

# Morse code dictionary
MORSE_CODE_DICT = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
    '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
    '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
    '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
    '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
    '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
    '...--': '3', '....-': '4', '.....': '5', '-....': '6',
    '--...': '7', '---..': '8', '----.': '9'
}

# GPIO Configuration
button_pin = Pin(4, Pin.IN, Pin.PULL_DOWN)
morse_code = ""
decoded_message = ""

# Timing Constants
DOT_TIME = 0.9  # Short press (dot) threshold: < 1.3 seconds
DASH_TIME = 1.5  # Long press (dash) threshold: >= 1.5 seconds
CHARACTER_PAUSE = 2.0  # Pause between characters


# Initialize web server
app = Microdot()

async def detect_morse():
    """Monitor the button and record dots, dashes, and pauses."""
    global morse_code, decoded_message
    last_state = 0
    press_start_time = 0

    print("detect_morse is running")
    while True:
        current_state = button_pin.value()
        current_time = time.ticks_ms()  # Use ticks_ms for millisecond precision

        if current_state == 1 and last_state == 0:  # Button press detected
            press_start_time = current_time
            last_state = 1
            print("Button pressed, start timing")

        elif current_state == 0 and last_state == 1:  # Button release detected
            press_duration = time.ticks_diff(current_time, press_start_time) / 1000.0  # Convert ms to seconds
            print(f"Press duration: {press_duration:.2f} seconds")
            if press_duration < DOT_TIME:
                morse_code += "."
                print("Dot detected")
            elif press_duration >= DOT_TIME:# and press_duration < DASH_TIME:
                morse_code += "-"
                print("Dash detected")
            else:
                print("Ignored long press")
            last_state = 0

        # Handle character decoding after a pause
        if current_state == 0 and last_state == 0 and (time.ticks_diff(current_time, press_start_time) > CHARACTER_PAUSE * 1000):
            if morse_code:
                decoded_message += MORSE_CODE_DICT.get(morse_code, "?")
                print(f"Character decoded: {decoded_message[-1]}")
                morse_code = ""

        await asyncio.sleep(0.001)  # Avoid busy-waiting




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
    try:
        with open("index.html", "r") as file:
            html_content = file.read()
        return html_content, 200, {"Content-Type": "text/html"}
    except OSError:
        return "Error: index.html not found", 404


@app.route("/message")
def message(request):
    return {"morse": morse_code, "message": decoded_message}


def run_web_server():
    """Run the Microdot web server."""
    app.run(port=5000, debug=True)


async def main():
    """Main entry point for the program."""
    print("Starting main program")

    # Set up Access Point
    setup_ap()

    # Start the web server in a separate thread
    start_new_thread(run_web_server, ())

    # Run the button detection task
    await detect_morse()


# Run the asyncio main loop
asyncio.run(main())






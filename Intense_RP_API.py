import threading, itertools, logging, socket, time, json, re, os
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from flask import Flask, request, jsonify
from colorama import init, Fore, Style
from selenium import webdriver

config_file = "config.json"
default_config = {"browser": "edge", "cookie": "Your cookie code.", "reset_context": True, "chat_txt": False, "url_bot": "https://poe.com/ChatGPT"}

if not os.path.exists(config_file):
    with open(config_file, "w") as cf:
        json.dump(default_config, cf, indent=4)

with open(config_file) as cf:
    config = json.load(cf)
    browser, cookie, reset_context, chat_txt, url_bot = config["browser"], config["cookie"], config["reset_context"], config["chat_txt"], config.get("url_bot")

browser_options = {"edge": webdriver.Edge, "chrome": webdriver.Chrome, "firefox": webdriver.Firefox}

if browser.lower() == "firefox":
    loading_chars = itertools.cycle(['|', '/', '-', '\\'])
    main_thread_should_exit = threading.Event()
    def loading_animation():
        try:
            while not main_thread_should_exit.is_set():
                char = next(loading_chars)
                print(f"\rWait a moment {char}", end='', flush=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass

    loading_thread = threading.Thread(target=loading_animation)
    loading_thread.start()

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)

if browser.lower() in browser_options:
    driver = browser_options[browser.lower()]()
    driver.get("https://poe.com")
    
    if browser.lower() == "firefox":
        cookie_dict = {"name": "p-b", "value": cookie}
        driver.add_cookie(cookie_dict)
        driver.get(url_bot)

@app.route('/models', methods=['GET'])
def sage_models():
    data = [{"id": "babbage", "object": "model", "created": 1649358449, "owned_by": "openai", "permission": [{"id": "modelperm-49FUp5v084tBB49tC4z8LPH5", "object": "model_permission", "created": 1669085501, "allow_create_engine": False, "allow_sampling": True, "allow_logprobs": True, "allow_search_indices": False, "allow_view": True, "allow_fine_tuning": False, "organization": "*", "group": None, "is_blocking": False }], "root": "babbage", "parent": None }, {"id": "text-davinci-003", "object": "model", "created": 1669599635, "owned_by": "openai-internal", "permission": [{"id": "modelperm-jepinXYt59ncUQrjQEIUEDyC", "object": "model_permission", "created": 1688551385, "allow_create_engine": False, "allow_sampling": True, "allow_logprobs": True, "allow_search_indices": False, "allow_view": True, "allow_fine_tuning": False, "organization": "*", "group": None, "is_blocking": False }], "root": "text-davinci-003", "parent": None }]
    print("- " + Fore.BLUE + Style.BRIGHT + "Connected!")
    return jsonify({"object": "list", "data": data})

@app.route('/chat/completions', methods=['POST'])
def sagedriver_completion():
    put_data = json.loads(request.get_data(as_text=True))
    
    messages = put_data.get("messages", [])
    if len(messages) >= 2 and messages[-1].get("role") == 'system' and messages[-2].get("role") == 'system':
        messages.pop(-2)
    formatted_messages = [f"{msg.get('role', '')}: {msg.get('content', '')}" for msg in messages]
    
    Character_Info = "\n\n".join(formatted_messages).replace("system: ", "")
    Character_Info = re.sub(r"(\w+): (\w+): ", r"\1: ", Character_Info)
    characterName = re.search(r'DATA1: "([^"]*)"', Character_Info).group(1) if re.search(r'DATA1: "([^"]*)"', Character_Info) else 'Character'
    userName = re.search(r'DATA2: "([^"]*)"', Character_Info).group(1) if re.search(r'DATA2: "([^"]*)"', Character_Info) else 'User'
    
    Character_Info = Character_Info.replace("assistant:", characterName + ":").replace("user:", userName + ":")
    Character_Info = "[Important Information]\n" + Character_Info
    
    if chat_txt:
        with open("Temp_CharInfo.txt", "w") as temp_file:
            temp_file.write(Character_Info)  
    print("\n- " + Fore.MAGENTA + Style.BRIGHT + "Information extracted.")
    
    if reset_context:
        try:
            driver.find_element(By.CSS_SELECTOR, '[class*="ChatMessageInputFooter_chatBreakButton"]').click()
            print("- " + Fore.YELLOW + Style.BRIGHT + "Context cleaned.")
        except NoSuchElementException:
            pass
    time.sleep(0.2)

    text_id = '[class*="GrowingTextArea_textArea"]'
    file_input = '[class*="ChatMessageFileInputButton_input"]'
    send_button = '[class*="ChatMessageSendButton_sendButton"]'

    try:
        text_area = driver.find_element(By.CSS_SELECTOR, text_id)
        driver.execute_script("arguments[0].value = arguments[1];", text_area, "." if chat_txt else Character_Info)
        text_area.send_keys(" ")

        if chat_txt:
            driver.find_element(By.CSS_SELECTOR, file_input).send_keys(os.path.abspath("Temp_CharInfo.txt"))
            time.sleep(0.5)
        print("- " + Fore.GREEN + Style.BRIGHT + "Message sent.")
    except NoSuchElementException:
        print("- " + Fore.RED + Style.BRIGHT + "The information could not be pasted.")
        return "Text box not found"

    text_area.send_keys(Keys.RETURN)
    print("- " + Fore.YELLOW + Style.BRIGHT + "Awaiting response.")
    time.sleep(2)

    text_area = driver.find_element(By.CSS_SELECTOR, text_id)
    driver.execute_script("arguments[0].value = arguments[1];", text_area, "Message to continue")
    text_area.send_keys(".")
    
    while True:
        try:
            if driver.find_element(By.CSS_SELECTOR, send_button).get_attribute("disabled") != "true":   
                break 
            time.sleep(0.2) 
        except NoSuchElementException:
            break

    if chat_txt:
        os.remove("Temp_CharInfo.txt")

    div = driver.find_elements(By.CSS_SELECTOR, '[class*="Markdown_markdownContainer"]')[-1]
    ResponsePoe = re.sub('<div class="Markdown_markdownContainer__.*">', '', div.get_attribute('outerHTML')).replace('<em>', '*').replace('</em>', '*').replace('<br>', '').replace('</br>', '').replace('<p>', '').replace('</p>', '').replace('</a>', '').replace('<code node="\\\[object Object\\\]">', '').replace('</code>', '').replace('</div>', '')
    
    if re.search(r'\[Important Information\]', ResponsePoe) or ResponsePoe == ".":
        ResponsePoe = "There was a problem with Poe"
        print("- " + Fore.RED + Style.BRIGHT + "A problem was detected.")
    else:
        print("- " + Fore.BLUE + Style.BRIGHT + "Response sent.")

    response_data = {"id": "chatcmpl-7ep1aerr8frmSjQSfrNnv69uVY0xM", "object": "chat.completion", "created": int(time.time() * 1000), "model": "gpt-3.5-turbo-0613", "choices": [{"index": 0, "message": {"role": "assistant", "content": f"{ResponsePoe}"}, "finish_reason": "stop" }], "usage": {"prompt_tokens": 724, "completion_tokens": 75, "total_tokens": 799}}
    return jsonify(response_data)
    
@app.route('/api/completions', methods=['GET'])
def api_completions():
    data = [{"id": 3}, {"id": 1}, {"id": 5}, {"id": 2}, {"id": 4}]
    return jsonify({"data": data})

if __name__ == '__main__':
    if browser.lower() == "firefox":
        main_thread_should_exit.set()
        loading_thread.join()
    init(autoreset=True)
    os.system("cls")
    print(Fore.MAGENTA + Style.BRIGHT + "API is now active!")    
    local_ip = socket.gethostbyname(socket.gethostname())
    time.sleep(0.2)
    print(Fore.CYAN + Style.BRIGHT + "WELCOME TO INTENSE RP API V1.4")
    time.sleep(0.2)
    print(Fore.GREEN + Style.BRIGHT + "Links to connect SillyTavern with the API:")
    time.sleep(0.2)
    print(Fore.YELLOW + Style.BRIGHT + f"URL 1: {Fore.WHITE}http://127.0.0.1:5000/")
    time.sleep(0.2)
    print(Fore.YELLOW + Style.BRIGHT + f"URL 2: {Fore.WHITE}http://{local_ip}:5000/")  
    time.sleep(0.2)
    app.run(host='0.0.0.0', port=5000)
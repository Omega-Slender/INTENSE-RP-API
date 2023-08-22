# Librerías.
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from colorama import init, Fore, Style
import threading
import itertools
import logging
import socket
import time
import json
import sys
import re
import os

# Si no existe el archivo Json, se crea.
if not os.path.exists("config.json"):
    default_config = {
        "browser": "edge",
        "cookie": "Your cookie code.",
        "reset_context": True
    }
    with open("config.json", "w") as config_file:
        json.dump(default_config, config_file, indent=4)

# Abrir Json y obtener la configuración.
with open("config.json") as config_file:
    config = json.load(config_file)
    browser = config["browser"]
    cookie = config["cookie"]
    reset_context = config["reset_context"]

# Verificar si el navegador es compatible, sino, mostrar mensaje y cerrar la consola.
if browser.lower() not in ["edge", "firefox", "chrome"]:
    init(autoreset=True)
    print("- " + Fore.RED + Style.BRIGHT + "Unsupported browser specified.")
    time.sleep(5)
    exit()

# Animación de carga para los navegadores compatibles.
if browser.lower() in ["firefox"]:
    loading_chars = itertools.cycle(['|', '/', '-', '\\'])

    def loading_animation():
        try:
            while not main_thread_should_exit.is_set():
                char = next(loading_chars)
                print(f"\rWait a moment {char}", end='', flush=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
            
    main_thread_should_exit = threading.Event()
    loading_thread = threading.Thread(target=loading_animation)
    loading_thread.start()

# Ocultar registros.
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)

# Inicialización de Selenium y abrir POE según el navegador especificado.
if browser.lower() == "edge":
    driver = webdriver.Edge()
elif browser.lower() == "chrome":
    driver = webdriver.Chrome()
elif browser.lower() == "firefox":
    driver = webdriver.Firefox()

driver.get("https://poe.com")

# Aplicar las Cookies solo si el navegador es Firefox.
if browser.lower() == "firefox":
    cookie_dict = {
        "name": "p-b",
        "value": cookie
    }
    driver.add_cookie(cookie_dict)

    # Reiniciar página.
    driver.refresh()

# Datos para conectarse a la API.
@app.route('/v2/driver/sage/models', methods=['GET'])
def sage_models():
    data = [
        {
            "id": "babbage",
            "object": "model",
            "created": 1649358449,
            "owned_by": "openai",
            "permission": [
                {
                    "id": "modelperm-49FUp5v084tBB49tC4z8LPH5",
                    "object": "model_permission",
                    "created": 1669085501,
                    "allow_create_engine": False,
                    "allow_sampling": True,
                    "allow_logprobs": True,
                    "allow_search_indices": False,
                    "allow_view": True,
                    "allow_fine_tuning": False,
                    "organization": "*",
                    "group": None,
                    "is_blocking": False
                }
            ],
            "root": "babbage",
            "parent": None
        },
        {
            "id": "text-davinci-003",
            "object": "model",
            "created": 1669599635,
            "owned_by": "openai-internal",
            "permission": [
                {
                    "id": "modelperm-jepinXYt59ncUQrjQEIUEDyC",
                    "object": "model_permission",
                    "created": 1688551385,
                    "allow_create_engine": False,
                    "allow_sampling": True,
                    "allow_logprobs": True,
                    "allow_search_indices": False,
                    "allow_view": True,
                    "allow_fine_tuning": False,
                    "organization": "*",
                    "group": None,
                    "is_blocking": False
                }
            ],
            "root": "text-davinci-003",
            "parent": None
        }
    ]
    print("- " + Fore.BLUE + Style.BRIGHT + "Connected!")
    return jsonify({"object": "list", "data": data})

# Recibir información para que POE pueda dar respuesta.
@app.route('/v2/driver/sage/chat/completions', methods=['POST'])
def sagedriver_completion():
    # Cargar los datos JSON de la solicitud externa de PUT.
    put_data = json.loads(request.get_data(as_text=True))

    # Encontrar los "[Start a new chat]"
    new_chat_indices = [i for i, msg in enumerate(put_data.get("messages", [])) if msg.get("content") == "[Start a new chat]"]

    # Cambiar todos los mensajes previos "[Start a new chat]" a "[Example Chat]"
    if len(new_chat_indices) > 0:
        for idx in new_chat_indices[:-1]:
            put_data["messages"][idx]["content"] = "[Example Chat]"

    # Verificar si hay al menos dos mensajes y ambos son de 'system'
    messages = put_data.get("messages", [])
    if len(messages) >= 2 and messages[-1].get("role") == 'system' and messages[-2].get("role") == 'system':
        messages.pop(-2)  # Eliminar el penúltimo mensaje si cumple la condición
        
    # Ordenar contenido del Json.
    formatted_messages = []
    for msg in put_data.get("messages", []):
        role = msg.get("role", "")
        content = msg.get("content", "")
        formatted_messages.append(f"{role}: {content}")

    # Agregar saltos de linea en el contenido.
    Character_Info = "\n\n".join(formatted_messages)
    
    # Quitar todo los "system:" del contenido.
    Character_Info = Character_Info.replace("system: ", "")
    
    # Eliminar nombres duplicados.
    regex = re.compile(r"(\w+): (\w+): ") 
    Character_Info = regex.sub(r"\1: ", Character_Info)
    
    # Detectar "DATA" y agregarlos en una variable.
    character_match = re.search(r'DATA1: "([^"]*)"', Character_Info)
    if character_match:
        characterName = character_match.group(1)
    else:
        characterName = 'Character:'
    
    user_match = re.search(r'DATA2: "([^"]*)"', Character_Info)
    if user_match:
        userName = user_match.group(1)
    else:
        userName = 'User:'

    # Reemplazar "assistant" y  "user" por unas variables.
    Character_Info = Character_Info.replace("assistant:", characterName)
    Character_Info = Character_Info.replace("user:", userName)
    
    # Dividir el contenido en dos partes
    split_content = re.split(r'(\[Start a new chat\])', Character_Info, maxsplit=1)
    Character_Info1 = split_content[0].strip()
    Character_Info2 = split_content[1] + '\n' + split_content[2].strip()
    print("\n- " + Fore.MAGENTA + Style.BRIGHT + "Information extracted.")

    # Presionar botón para reiniciar contexto.
    if reset_context:
        try:
            reset = driver.find_element(By.CLASS_NAME, "ChatMessageInputFooter_chatBreakButton__hqJ3v")
            reset.click()
            print("- " + Fore.YELLOW + Style.BRIGHT + "Context cleaned.")
        except NoSuchElementException:
            pass
    
    # Avisar que el proceso terminó.
    time.sleep(0.1)
    
    try:
        # Agregar caja de texto en una variable.
        text_area = driver.find_element(By.CLASS_NAME, "GrowingTextArea_textArea__eadlu")
        
        # Ejecutar script para pegar la infomación.
        driver.execute_script("arguments[0].value = arguments[1];", text_area, Character_Info1)
        text_area.send_keys("\n\n[If you accept the requirements, please confirm by responding with \"Understood.\" and nothing more. Once I receive your precise confirmation message, I will specify the context of the scene, as well as the characteristics, background, and personality of your character in the following message.]")
        
    except NoSuchElementException:
        # Lanzar error cuando no se cuentre la caja de texto.
        print("- " + Fore.RED + Style.BRIGHT + "The information could not be pasted.")
        return "Text box not found"

    # Presionar ENTER para enviar "Character_Info1" y avisar en la consola.
    text_area.send_keys(Keys.RETURN)
    print("- " + Fore.GREEN + Style.BRIGHT + "Message one sent.")
    print("- " + Fore.YELLOW + Style.BRIGHT + "Awaiting response.")
    
    # Esperar 2 segundos para poder enviar el contenido de "Character_Info2".
    time.sleep(2)
    text_area = driver.find_element(By.CLASS_NAME, "GrowingTextArea_textArea__eadlu")
    driver.execute_script("arguments[0].value = arguments[1];", text_area, Character_Info2)
    text_area.send_keys(" ")
    
    # Revisar en bucle si el botón de enviar está disponible.
    while True:
        try:
            send_button = driver.find_element(By.CLASS_NAME, "ChatMessageSendButton_sendButton__OMyK1")
            if send_button.get_attribute("disabled") == "true":   
                time.sleep(0.2) 
            else:
                break 
        except NoSuchElementException:
            break

    # Presionar otra vez ENTER para enviar "Character_Info2" y avisar en la consola.
    text_area.send_keys(Keys.RETURN)
    print("- " + Fore.GREEN + Style.BRIGHT + "Message two sent.")
    print("- " + Fore.YELLOW + Style.BRIGHT + "Awaiting response.")
    
    # Esperar 2 segundos para poder enviar el texto.
    time.sleep(2.5)
    text_area = driver.find_element(By.CLASS_NAME, "GrowingTextArea_textArea__eadlu")
    driver.execute_script("arguments[0].value = arguments[1];", text_area, "Message to continue")
    text_area.send_keys(".")
    
    # Revisar en bucle si el botón de enviar está disponible.
    while True:
        try:
            send_button = driver.find_element(By.CLASS_NAME, "ChatMessageSendButton_sendButton__OMyK1")
            if send_button.get_attribute("disabled") == "true":   
                time.sleep(0.2) 
            else:
                break 
        except NoSuchElementException:
            break

    # Obtener el contenido de la última respuesta.
    div = driver.find_elements(By.CSS_SELECTOR, "div.Markdown_markdownContainer__UyYrv")[-1]
    content = div.get_attribute('outerHTML')
    ResponsePoe = content
    time.sleep(0.1)
    
    # Limpiar contenido de la respuesta y avisar que terminó el proceso.
    ResponsePoe = ResponsePoe.replace('<em>', '*').replace('</em>', '*')
    ResponsePoe = ResponsePoe.replace('<br>', '').replace('</br>', '').replace('<p>', '').replace('</p>', '').replace('<a node="\\\[object Object\\\]" class="MarkdownLink_linkifiedLink__KxC9G">', '').replace('</a>', '').replace('<code node="\\\[object Object\\\]">', '').replace('</code>', '').replace('<div class="Markdown_markdownContainer__UyYrv">', '').replace('</div>', '')
    ResponsePoe = re.sub(r'^[^\n]+:', '', ResponsePoe, flags=re.MULTILINE).strip()

    # Detectar si existe botón de bloqueo.
    try:
        last_markdown_container = driver.find_elements(By.CLASS_NAME, "Markdown_markdownContainer__UyYrv")[-1]
        bot_message = last_markdown_container.find_element(By.XPATH, ".//following::div[contains(@class, 'Message_botMessageBubble__CPGMI') and contains(@class, 'Message_widerMessage__SmSLi')]")
        print("- " + Fore.RED + Style.BRIGHT + "A problem was detected.")
        ResponsePoe = "There was a problem with POE."
        # Continuar con el código aquí después de encontrar el mensaje del bot.
    except NoSuchElementException:
        print("- " + Fore.GREEN + Style.BRIGHT + "Response cleaned.")
    
    # Enviar respuesta.
    response_data = {
        "id": "chatcmpl-7ep1aerr8frmSjQSfrNnv69uVY0xM",
        "object": "chat.completion",
        "created": int(time.time() * 1000),
        "model": "gpt-3.5-turbo-0613",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"{ResponsePoe}"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 724,
            "completion_tokens": 75,
            "total_tokens": 799
        }
    }
    print("- " + Fore.BLUE + Style.BRIGHT + "Response sent.")
    return jsonify(response_data)
    
@app.route('/api/completions', methods=['GET'])
def api_completions():
    data = [
        {"id": 3},
        {"id": 1},
        {"id": 5},
        {"id": 2},
        {"id": 4}
    ]
    return jsonify({"data": data})

init(autoreset=True)

if __name__ == '__main__':
    if browser.lower() in ["firefox"]:
        main_thread_should_exit.set()
        loading_thread.join()
    os.system("cls")
    print(Fore.MAGENTA + Style.BRIGHT + "API is now active!")    
    local_ip = socket.gethostbyname(socket.gethostname())
    time.sleep(0.2)
    
    print(Fore.CYAN + Style.BRIGHT + "WELCOME TO INTENSE RP API V1.1")
    time.sleep(0.2)

    print(Fore.GREEN + Style.BRIGHT + "Links to connect SillyTavern with the API:")
    time.sleep(0.2)
    
    print(Fore.YELLOW + Style.BRIGHT + f"URL 1: {Fore.WHITE}http://127.0.0.1:5000/v2/driver/sage")
    time.sleep(0.2)
    
    print(Fore.YELLOW + Style.BRIGHT + f"URL 2: {Fore.WHITE}http://{local_ip}:5000/v2/driver/sage")  
    time.sleep(0.2)
    app.run(host='0.0.0.0', port=5000)
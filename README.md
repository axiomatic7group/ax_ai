# Ax AI Operating System

[![Watch the Quick Demo](https://shields.io/badge/Watch%20the%20Quick%20Demo-blue)](https://www.youtube.com/watch?v=8NkYYi3W8k0&list=PLB8Oz6sV8GaY)
![AxAI](https://img.shields.io/badge/AxAI%20OS-blue)
![License](https://img.shields.io/badge/license-pache--2.0-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)

# 1. Get started with Ax AI in less than 10 minutes

### 1.1 Table of Contents

* 1. Getting Started
    * Features
    * Video Guide Series - Unwrapping AI
    * Prerequisites
* 2. **Quick Start & Installation** - link
* 3. How-To Guides - Video Series and Practical Use Cases
* 4. Roadmap - What's next

### 1.2 Features

* **Local First AI Chat**: Easily find and deploy AI models locally based on your computer's capacity.
* **Audio, Local Files, & Websearch Tools**: AI can safely and securily: 
    * take notes of meeting recordings, 
    * get and organize data from local files, 
    * search the web, 
    * and more, **all locally and securely in your computer**.
* **AI Chat Summaries**: Summarize plans, barinstorming sessions, or just general conversations you with your private AI.
* **Optimized for Local Deployment**: AI Personalities, token pruning, and more functions design for efficient and simple local AI deployement. No coding or technical expertise needed. 

### 1.3 Video Guide Series - Unwrapping AI
<br>

From local agents and automated meeting notes to cleaning leads and managing client notes, follow our YT series to learn both what Ax AI can do for your business, as well as, how to set evertyhing up in less than 1 hour. 

| Episode | Topic | Business Topic | Markdown Reference |
|---|---|---|---|
| Ep 1: Installation & Setup | [Quick Guide](https://www.youtube.com/watch?v=GYdxLapCx2c) ~2mins | [Easy & Secure Local AI](https://www.youtube.com/watch?v=pkXRfhG60oU) ~9 mins | [See Steps Below](# 2. Quick Start & Installation) |
| Ep 2: How Audio Notes Works | Quick Guide - coming soon | Free Granola Notetaker  ~9 mins | [See Steps Below](###     3.1.2 How audio tool works) |
| Ep 3: How Local Files Works | Quick Guide - coming soon | Easy & Secure Local RAG  ~9 mins | [See Steps Below](###     3.1.3 How local tool files works) |
| Ep 4: How Websearch Works | Quick Guide - coming soon | Don't Waste time with Bad Leads  ~9 mins | [See Steps Below](###     3.1.4 How websearch tool works)|




###  1.4 Prerequisites
List exactly what needs to be installed on the host machine before your app can run. Provide exact version ranges to avoid environment conflicts.

* #### Prerequisite 1: How to install Docker - [YouTube Video](https://www.youtube.com/watch?v=GYdxLapCx2c) 

    #### Quick Guide 

    ------------------------------
    #### Windows
        ```
        1. Make sure WSL 2 (Windows Subsystem for Linux) is enabled on your PC.
        2. Download the installer from the [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) page.
        3. Run the .exe file and check the box to enable WSL 2 when prompted.
        4. Restart your computer.
        5. Open Docker Desktop from your start menu and accept the terms.
        6. Open your terminal (Command Prompt or PowerShell) and test it: [3, 4, 5, 6] 
        
        docker --version
        ```
    
    ------------------------------
    #### Mac (macOS)
        ```
        1. Go to the Docker Desktop for Mac page and choose Intel or Apple Silicon (M1/M2/M3/M4).
        2. Download and open the .dmg file.
        3. Drag the Docker icon into your Applications folder.
        4. Open Docker from your Applications folder and grant permissions.
        5. Open your terminal and verify the setup: [2, 7, 8] 
        
        docker --version
        ```
        
    ------------------------------
    #### Linux (Ubuntu / Debian example)
        ```

        1. Update your package manager and install helper tools:
        
        sudo apt update
        sudo apt install ca-certificates curl
        
        2. Add Docker’s official GPG key and repository:
        
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        
        3. Set up the repository and install Docker Engine:
        
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
        sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        
        4. Start and enable the service:
        
        sudo systemctl start docker
        sudo systemctl enable docker
        
        5. Test your installation: [1, 2, 3, 9] 
        
        sudo docker run hello-world

        ```

* #### Prerequisite 2: How to check computer RAM/VRAM 

    #### Quick Guide:

    
    #### Windows
        ## Check RAM

        * Press Ctrl + Shift + Esc to open Task Manager.
        * Go to the Performance tab and click Memory.

        ## Check VRAM

        * Open Task Manager (Ctrl + Shift + Esc).
        * Go to the Performance tab and click GPU.
        * Look for Dedicated Video Memory at the bottom.

    ------------------------------
    #### Mac (macOS)
        ## Check RAM

        * Click the Apple icon () in the top-left corner.
        * Select About This Mac (or System Settings > General > About).
        * Look for Memory.

        ## Check VRAM

        * On Apple Silicon (M1/M2/M3/M4) Macs, RAM and VRAM are shared dynamically from a single pool of Unified Memory. Whatever your total memory is, your graphics system can access it as needed.
        * On older Intel Macs, click the Apple icon > About This Mac and look for the Graphics line to see the dedicated VRAM amount.

    ------------------------------
    #### Linux
        ## Check RAM
        Open your terminal and run the following command for a clean, human-readable breakdown:

        free -h

        ## Check VRAM
        Depending on your graphics hardware, use one of these quick terminal commands:

        * NVIDIA GPUs:

        nvidia-smi

        (Look for the Memory-Usage column to see your total VRAM.)
        * AMD / Intel / General GPUs:

        sudo apt install radeontop  # For AMD tracking# OR use a universal tool:
        sudo apt install nvtop
        nvtop

<br>
<br>
<br>
<br>

# 2. Quick Start & Installation 

### 2.1 Install Ax AI Using Docker - [Link to YT Video](https://www.youtube.com/watch?v=GYdxLapCx2c)
Step by step install process for Ax AI

```
# Clone the repository

git clone https://github.com/axiomatic7group/ax_ai
cd ax_ai

# Run the setup script or container initialization and this will start and run your docker image as well

docker-compose up --build -d

# go to -> http://127.0.0.1:8000/ on your browser to see if it works 

```

### 2.2 Getting Started - [Link to YT Video](https://www.youtube.com/watch?v=pkXRfhG60oU)
Show a literal, realistic example of your configuration format. Use high-contrast code blocks with realistic dummy data instead of abstract placeholders.

```
# Create User
    go to - http://127.0.0.1:8000/signup/

    values = {
        user_name = your unique username
        password = your secure password 
    }


# Add base personality
    go to - http://127.0.0.1:8000/daemon/new_model_personality/

    values = {
        personality_name = "chat"
        personality_description = "You are an AI chat assistant."
        personality_type = 'behavior'
        personality_temp = 0.7
        personality_top_p = 0.9
    }

# Add local model base and model base user

    go to - http://127.0.0.1:8000/daemon/new_model/

    New Connection Tab - Create Model Base

    values = {
        model_base_name = "local"
        model_base_url = "http://127.0.0.1:8080/"
    }

    go to again - http://127.0.0.1:8000/daemon/new_model/

    New Connection Tab - Add User Connection

    values = {
        model_base = "local"
        api_key = "-"
    }

    go to again - http://127.0.0.1:8000/daemon/new_model/

    New Connection Tab - New Model Connection

    values = {
        model_base = "local"
        model_name = "local_model"
    }

# Find and Initiate adequate local model
    go to -  http://127.0.0.1:8000/daemon/initiate_models/
    
    Use the marketplace tab to find and Download a model based on your compute
        Check RAM/VRAM guide if needed
    
    Click the model you would like to add to get started

    Once the page refreshes, go to the "Run Local Model" tab
    
    Pick "start", and the model you just choose to start using it
        * Note: the first time you run a new local model it will take longer to start as it needs to download the model to your computer first
        Subsequent runs will start up fast

# Start first chat with local model
    go to - http://127.0.0.1:8000/daemon/new_model_chat/

    Create a new chat, and go to - http://127.0.0.1:8000/daemon/model_chat_messages/1/
    
    And start chatting with your local AI

```

<br>
<br>
<br>
<br>

# 3. How-To Guides

##  3.1 How Messages & Tools Work

###     3.1.1 Main componenents of messages

The message input values users submit, aside from the user text prompt, has 4 input values:
 * personalities - these include both system instructions for your model, as well as, temperature and top_p values to use (inputs are based on model personalities)
 * model -  the model the you want to use to answer the prompt you are submiting (options are based on user model connections)
 * tool - fast, thinking, websearch, local files, audio files; help AI interact with different user input types 
 * file input - input value for local files and audio files

Aside from these five inputs, the model message input function requires 2 additional inputs, chat_summary & chat_history_list. To prevent context windows from getting too large while allowing you to continue with same chat history, we created **chat summaries**. Using the "Summarize this Chat" button in the model chat page, user can create a AI generated summary of their current chat, which can be view and manually edited by the user as well by clicking the "Chat Summary" button. The system tracks the messages that have been summarize so that future summaries will only cover the newest messagesa and update and add on to the old summary. 


```
def send_message_to_model(promt_message, user_request, chat_summary="", chat_tool="fast", personality="",
                        model_base="http://127.0.0.1:8080", model_name="local-model", model_api_key="dummy_key",  
                        chat_history_list=None, run_tempereature=0.75, top_p=0.9,):

    if isinstance(chat_history_list, pd.DataFrame):
        chat_history = []

        if len(chat_history_list) == 1:
            chat_history = []
        else:
            chat_history_list = chat_history_list[:-1]
            chat_history_list = chat_history_list.sort_values('date_created')
            
            system_msgs = chat_history_list[chat_history_list['chat_sender'] == "system"]
            chat_history_list = chat_history_list[chat_history_list['chat_sender'] != "system"]
            system_content = "\n\n".join(system_msgs['chat_message'].tolist()) if not system_msgs.empty else ""

            for i_message, e_message in chat_history_list.iterrows():
                role = e_message['chat_sender']
                content = e_message['chat_message']
                
                if not chat_history and role == "user" and system_content:
                    content = f"{system_content}\n\n{content}"

                if chat_history:
                    last_msg = chat_history[-1]
                    if (role == "user" and isinstance(last_msg, HumanMessage)) or (role == "model" and isinstance(last_msg, AIMessage)):
                        last_msg.content += f"\n\n{content}"
                        continue

                if role == "user":
                    chat_history.append(HumanMessage(content=reduce_tokens(content)))
                elif role == "model":
                    chat_history.append(AIMessage(content=reduce_tokens(content)))
```

###     3.1.2 How audio tool works - video link - 

Audio tools collects submitted mp3 files, it will convert the audio file using first FFmpeg to convert from mp3 to wav format, a format the AI models prefers. It then covnerts the wav audio file format to base64-encoded format so it can be safely sent and stored across text-only protocols without data corruption.

```
if user_request.FILES.get("filename"):
    uploaded_file = user_request.FILES["filename"]
    input_bytes = uploaded_file.read()

    process = subprocess.Popen(
        ["ffmpeg", "-i", "pipe:0", "-f", "wav", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "pipe:1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL)

    wav_bytes, _ = process.communicate(input=input_bytes)
    encoded_string = base64.b64encode(wav_bytes).decode('utf-8')

    messages_payload = [
        {"role": "system", "content": str(reduce_tokens(audio_personality))},
        {"role": "user", "content": 
            [{"type": "input_audio", "input_audio": {"data": encoded_string, "format": "wav" }},
            {"type": "text", "text": promt_message}]}]

    payload = {
        "model": "ultravox",
        "messages": messages_payload,
        "temperature": 0.15,
        "cache_prompt": True
    }

    response = requests.post("http://127.0.0.1:8080/v1/chat/completions", headers={"Content-Type": "application/json"}, json=payload,)

    temp_response = response.json()
    first_dict = {'choices': temp_response.pop('choices')}
    remaining_dict = temp_response
```

###     3.1.3 How local tool files works - video link

Local files tool works similarly to audio file tool, however, instead of converting the file types, they are "load". For AI to interact with localfiles, you can use pydantic loaders such as **TextLoader, PythonLoader, PyPDFLoader**; These help your model better understand the context of the data rather then just extracting all contents as a sting and passing that as context. 

```
def check_files(request):
    if os.path.isfile(str(request)):
        with open((request), "r", encoding="utf-8") as file:
            file_to_check = str(request)
            file_content = file.read()
    
    elif 'filename' not in request.FILES:
        return {'message': 'no file', 'state': '0'}
    else:
        file_to_check = request.FILES['filename']
        file_content = file_to_check.read()
    
    ...
    
    output = {}
    if not qs.results.get('exploits_found'):
        try:
            file_type = str(file_to_check.name).split(".")[-1].lower()
        except:
            file_type = str(file_to_check).split(".")[-1].lower()

        with NamedTemporaryFile(suffix=f".{file_type}") as tmp:
            try:
                tmp.write(file_content)
                tmp.flush()
                temp_name = tmp.name
            except:
                temp_name = str(file_to_check)
            
            if file_type == "txt" or file_type == "md":
                loader = TextLoader(temp_name, encoding='utf-8')
                
            elif file_type == "py":
                loader = PythonLoader(temp_name)
            
            elif file_type == "pdf":
                loader = PyPDFLoader(temp_name)

            else:
                return {'message': 'Unsupported type', 'state': '0'}
            
            docs = loader.load()
            full_text = "\n\n".join([doc.page_content for doc in docs])
            output["context"] = full_text
            output["state"] = "1"
    else:
        output = {'message': 'Error detected.', 'state': '0'}
    return output
```

###     3.1.4 How websearch tool works - video link

Generally, AI models used optimized API-based search tools to give their models access to websearch, however, these APIs are not free. In an effort to create a fully local and free AI system we put together a simple workaround. To use websearch, the system first tries to use python standard request to duckgo search to get a list of top links from the search engine results; When this does not work, the system does this using selenium. Once the list of links is collected, the system sends get requests to these links and scrapes the results to send as context to the model.

```
url = 'https://html.duckduckgo.com/html/'
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    params = {'q': search_query}
    headers = {'User-Agent': user_agent, 'Referer': 'https://duckduckgo.com/',}
    temp_html = requests.post(url, headers=headers, data=params)
    links_output = []
    print("start")
    if  temp_html.status_code == 200:
        soup = BeautifulSoup(temp_html.text, 'html.parser')
        links = soup.find_all('a', class_='result__a')
        for link in links:
            result_dict = {"text": link.get_text(strip=True), "url": link.get('href')}
            links_output.append(result_dict)
    else:
        print("start driver 1....")
        search_query_url = urllib.parse.quote_plus(search_query)
        url = 'https://duckduckgo.com/search?q=' + search_query_url
        url = 'https://html.duckduckgo.com/html/search?q=' + search_query_url
        user_agent_list = ["Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.517 Safari/537.36",]
        user_agent = random.choice(user_agent_list)
        headers = {'User-Agent': user_agent}

        sandbox_safe_tmp = os.path.expanduser("~/selenium_tmp")
        os.makedirs(sandbox_safe_tmp, exist_ok=True)
        os.environ["TMPDIR"] = sandbox_safe_tmp
        service = Service(
            executable_path="/usr/local/bin/geckodriver",
            log_path=os.path.join(sandbox_safe_tmp, "geckodriver.log")
        )

        options = Options()
        options.add_argument("-headless")
        options.set_preference("general.useragent.override", user_agent)
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        print("starting driver 2.....")
        driver = Firefox(options=options, service=service)
        print("starting driver 3.....")
        driver.get(url)


        links = driver.find_elements(By.TAG_NAME, 'a')
        print("check 1",links)
        for link in links:
            print("check 2",link)
            if link.text != '':
                result_dict = {"text": link.text, "url": link.get_attribute("href")}
                links_output.append(result_dict)
        driver.quit()
    
    links_output = links_output[:links_count]
    search_output = {}
    for i, link in enumerate(links_output):
        print(i, link)
        temp_html = requests.get(link['url'], headers = headers, params=params, timeout=15)
        soup = BeautifulSoup(temp_html.content,'lxml')
        if soup.find('main') is not None:
            soup = soup.find('main')
        for match in soup.find_all('span', 'sup'):
            match.unwrap()
        
        content = soup.find_all('p')
        if content == []:
            content = soup
        content = str(content).replace('</p>', '').replace('<p>', '').replace('</a>', '')
        content = reduce_tokens(str(content))
        if content != None:
            search_output['source '+str(i)] = {'url':link, 'context':content[:1500]}

    return search_output
```




###     3.1.5 How other tool works

**Thinking** tool in messsages activaties reasoning mode (only works if model has reasoning capacity)
**Fast** tool in messsages is the default and makes a simple non-reasoning query to the model

All of the tools use a standard token pruning function (reduce_tokens) to help minize token input costs.

```
def reduce_tokens(input_text):
    if isinstance(input_text, str):
        if len(input_text) != 0:            
            output_text = input_text.replace(' an ', '').replace(' the ', '').replace(' of ', '').replace(' is ', '').replace(' for ', '').replace(' in ', '')
                        
            return output_text
    
    else:
        return input_text
```

###     3.1.6 How message & message summaries work

I like having some very long chats with my models but when context windows got too large, the only "viable" solution was to have the model summarize the current chat and start a new chat. Although this is great for the model, I can no longer see the context of the previous messages as clearly. To address this very issue I create **"chat summaries."** The way it works is that when your chat gets too long, you can summarize the chat and it will ask your AI model to create a chat summary and save it. The system keeps track of the messages that have been summarized so that going forward they are removed from your models context window, so the model will only see the summary and not the old messages, but the user can still see all the messages. As the user and models chat after the summary, only the new chat messages will be used when creating the next chat summary you request, adding this summary to the previous. Summaries can be viewed and edit but users at any point. 

*Security note: the system natively asks the model to split any personal and indentifiable information from the general summary and it will store it in a seperate portion of the chat summary document that only the user can see. This is design to help prevent sharing information when using API AI models, by summarizing chats before using public API AI models like Claude or ChatGPT, these models only see the portions of your chat that matter for their tasks and none of your private information. 

#### Chat Summarize Function
```
def summarize_chat(model_chat_id, request):

    if model_chats.objects.filter(id=model_chat_id).exists:
        model_chats_to_sum = pd.DataFrame(model_chats.objects.filter(id=model_chat_id).values())
        temp_model_conn = model_connection.objects.get(id=model_chats_to_sum['model_connection_name_id'].iloc[0])
        chat_model_connection = pd.DataFrame(model_connection.objects.filter(id=model_chats_to_sum['model_connection_name_id'].iloc[0]).values())
        model_base_conn = model_base_user_connection.objects.get(chat_user=request.user, model_base_id=temp_model_conn.model_base.id)
        temp_model_base = model_base.objects.get(id=model_base_conn.model_base.id)


        chat_messages_to_sum = pd.DataFrame(chat_messages.objects.filter(message_model_chats_id=model_chat_id).values())
        check_chat_history = pd.DataFrame(chat_message_summarized.objects.filter(chat_message_id__in=chat_messages_to_sum['id'].to_list()).values())

        if check_chat_history.empty:
            if not internal_document.objects.filter(document_name='user_chat_summary__chat_id__'+str(model_chat_id)).exists():
                chat_summary_obj = internal_document.objects.create( date_created = timezone.now(),
                    document_name = 'user_chat_summary__chat_id__'+str(model_chat_id), document_object = {'user_chat': 'user_chat__'+str(model_chat_id),},
                    document_personality = model_personality.objects.get(id=2), document_type = "chat_summary",)
            else:
                "something went wrong with this chat summary"
                chat_summary_obj = internal_document.objects.get(document_name='user_chat_summary__chat_id__'+str(model_chat_id))
            
            checked_chat_history = chat_messages_to_sum
            chat_summary_version = 1          
        
        else:
            check_chat_history = check_chat_history[check_chat_history['chat_summarized']==True]
            checked_chat_history = chat_messages_to_sum[~chat_messages_to_sum['id'].isin(check_chat_history['chat_message_id'])]

            if internal_document.objects.filter(document_name='user_chat_summary__chat_id__'+str(model_chat_id)).exists():
                chat_summary_obj = internal_document.objects.get(document_name='user_chat_summary__chat_id__'+str(model_chat_id))        
                if internal_document_version.objects.filter(internal_document=chat_summary_obj).exists():
                    chat_summary_versions = internal_document_version.objects.filter(internal_document=chat_summary_obj)
                    chat_summary_versions_df = pd.DataFrame(chat_summary_versions.values())
                    latest_summary_version = chat_summary_versions_df[chat_summary_versions_df['document_version'] == chat_summary_versions_df['document_version'].max()]
                    
                    chat_summary_version = int(latest_summary_version['document_version'].iloc[0]) + 1
                else:
                    chat_summary_version = 1
            else:
                chat_summary_obj = internal_document.objects.create( date_created = timezone.now(),
                    document_name = 'user_chat_summary__chat_id__'+str(model_chat_id), document_object = {'user_chat': 'user_chat__'+str(model_chat_id),},
                    document_personality = model_personality.objects.get(id=2), document_type = "chat_summary",)
                
                chat_summary_version = 1

        run_model = ChatOpenAI( base_url=temp_model_base.model_base_url, 
                                api_key=model_base_conn.model_api_key,
                                model=chat_model_connection['model_name'].iloc[0], 
                                temperature=0.1, top_p=0.1)
        
        chat_history_list = checked_chat_history

        if isinstance(chat_history_list, pd.DataFrame):
            if chat_history_list.empty:
                return {"status":1, "message":"no new chats"}
            chat_history = []

            if len(chat_history_list) == 1:
                chat_history = []
            else:
                chat_history_list = chat_history_list.sort_values('date_created')
                
                system_msgs = chat_history_list[chat_history_list['chat_sender'] == "system"]
                chat_history_list = chat_history_list[chat_history_list['chat_sender'] != "system"]
                system_content = "\n\n".join(system_msgs['chat_message'].tolist()) if not system_msgs.empty else ""

                for i_message, e_message in chat_history_list.iterrows():
                    role = e_message['chat_sender']
                    content = e_message['chat_message']
                    
                    if not chat_history and role == "user" and system_content:
                        content = f"{system_content} \n  {content}"

                    if chat_history:
                        last_msg = chat_history[-1]
                        if (role == "user" and isinstance(last_msg, HumanMessage)) or (role == "model" and isinstance(last_msg, AIMessage)):
                            last_msg.content += f"\n  {content}"
                            continue

                    if role == "user":
                        chat_history.append(HumanMessage(content=reduce_tokens(content)))
                    elif role == "model":
                        chat_history.append(AIMessage(content=reduce_tokens(content)))

        class PrivateChatSummary(BaseModel):
            general_summary: str = Field(description="Summary of relevant information found in chat history.")
            private_summary: str = Field(description="All private information from chat history.")
        
        temp_prompt = ( "You are an AI assitant being obeserved for your efficiency and performance, "
        "analyze the chat history and create a detailed summary of relevant information to be used as a replacement for the chat history going forward;" \
        "Be sure to inlcude all the information that would be relevant for the conversation going forward if the chat history were removed;"
        "Be sure to collect and write down all private and personal, or professional information including client names and details only in the private summary;")
        run_model_w_struct = run_model.with_structured_output(PrivateChatSummary)
        user_prompt = ChatPromptTemplate.from_messages([("system", "{system_context}"), MessagesPlaceholder(variable_name="chat_history"), ("human", "{promt_message}"),])
        chain = user_prompt | run_model_w_struct
        summaries_list = chain.invoke({"promt_message": temp_prompt, "system_context": summary_personality, "chat_history":chat_history})

        temp_new_chat_summary = internal_document_version.objects.create( date_created = timezone.now(), document_text = summaries_list.general_summary,
            document_notes = summaries_list.private_summary, document_version = chat_summary_version, internal_document = chat_summary_obj,)

        checked_chat_history_check = pd.DataFrame()
        checked_chat_history_check['chat_message'] = [chat_messages.objects.get(id=x) for x in checked_chat_history['id']]
        checked_chat_history_check['date_summairzed'] = timezone.now()
        checked_chat_history_check['chat_summarized'] = True

        instances = [chat_message_summarized(**row) for row in checked_chat_history_check.to_dict('records')]
        chat_message_summarized.objects.bulk_create(instances)
        return {"status":1, "message":"chat summarized"}
    
    else:
        return {"status":0, "message":"chat NOT summarized"}
```

<br>
<br>
<br>
<br>

# 4. Roadmap - what to expect next

## Other Tools -  Cadence, Synapse, Portfolio
## Future Apps -  CRM/GTM Agent, CoS Agent, Financial Analyst Agent, Study Agent, & more. 



## Ax(iomatic) Lab is an Open-Source Lab developing the "No-Frills" AI solutions businesses actually want  

After years of watching the large organization I worked for spend millions of dollars per year on subpar enterprise software solutions that could not be replaced due to **Big Tech contract entrapment**, I thought, there has to be a better solution. So I started Ax Lab, with the purpose of bringing to life all the tools and functionalities that a well-managed and productive enterprise would need. 

I strongly believe that the winners of AI are going to be the businesses that find the best and most productive ways to implement this technology to help their business be more competitive. To promote fair competition and give small and medium size businesses (SMBs/SMEs), startups, and all entrepreneurs the opportunity to show how they can leverage AI to make more productive and competitive businesses, I have decided to focus the **primary** efforts of Ax Lab in producing Open-Source tools that anyone can use for free and build upon.    


If you are a entrepreneur, small business owner, or startup founder, looking for the No-Hype AI solutions for your business, let’s talk.

  - Get a Free AI Strategy <a href="https://axiomaticlab.com/portfolio/service/best-ai-strategy-for-smbs" target="_blank"> Audit! </a>


  - See our tools in action and learn more in our <a href="https://www.youtube.com/@axiomatic_lab?sub_confirmation=1" target="_blank"> YouTube Channel </a>

If you are a developer or enthusiast looking to learn more about Open-Source tools, **explore our core open-source architecture:**
- <a href="https://github.com/axiomatic7group" target="_blank"> Axiom AI - all-in-on AI Operating System </a>
- <a href="https://axiomaticlab.com/portfolio/project/daemon" target="_blank"> Daemon - Local AI Chatbot </a>
- <a href="https://axiomaticlab.com/portfolio/project/synapse" target="_blank"> Synapse - Ontology & Advanced Semantic Layer Management </a>
- <a href="https://axiomaticlab.com/portfolio/project/cadence" target="_blank"> Cadence - Project & Client Relationship Management </a>
- <a href="https://github.com/axiomatic7group/ax_portfolio" target="_blank"> Portfolio - Website & Leads Funnel </a>


------------------------------

## The Team

**Daniel Marques**  -  Founder - <a href="https://www.linkedin.com/in/daniel-encarnacao/" target="_blank"> LinkedIn Profile </a> 

Daniel is an executive finance and operations leader with over six years of experience accelerating technological and operational development within Tier-1 financial institutions. Prior to launching Axiomatic Lab, Daniel operated as the Head of the CFO Solutions at a Top-10 Global Investment Bank in New York. In this capacity, he directed the AI-driven data automation strategies that achieved $35M in operational efficiencies, cut reporting turnaround times by 25%, and reduced 85% of human errors across critical regulatory reporting data streams. 

If you would like to collaborate on any of our open-source projects, please reach out on here or LinkedIn; Always happy to grow the community

### **Contact us today: [axiomaticlab.com](https://axiomaticlab.com/contact/)**

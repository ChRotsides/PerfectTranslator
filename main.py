import os
import openai
import tiktoken
from textblob import TextBlob
import PySimpleGUI as sg
import random
from dotenv import load_dotenv
from threading import Thread
import time
load_dotenv()

try:
    api_key=os.environ.get("OPENAI_API_KEY")
    openai.api_key = api_key
except:
    print("OpenAI API Key not found")
    exit()

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    # encoding = tiktoken.get_encoding(encoding_name)
    encoding = tiktoken.encoding_for_model("gpt-4")
    num_tokens = len(encoding.encode(string))
    return num_tokens

# def num_tokens_from_string(string: str, encoding_name: str) -> int:
#     """Returns the number of tokens in a text string."""
    
#     # Assuming you want to use the Hugging Face transformers library for encoding
#     try:
#         from transformers import AutoTokenizer
#     except ImportError:
#         raise ImportError("Please install transformers library.")

#     # Load the tokenizer
#     tokenizer = AutoTokenizer.from_pretrained(encoding_name)
#     wrapper = TokenizerWrapper(tokenizer)

#     # Tokenize the string and count the number of tokens
#     tokens = wrapper.encode(string)
#     num_tokens = len(tokens)

#     return num_tokens

def fix_grammar(string,index):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a specialist in the refinement of Greek grammar, punctuation, and syntax"},
            {"role": "user", "content": "Greek text from the translation of the \"Short stories from 100 Selected Stories, by O Henry\": "+ string},
            {"role": "assistant", "content": "You have to fix the grammar, punctuation, and syntax of the text in greek"},
            # {"role": "user", "content": "Where was it played?"}
        ]
    )
    result=response['choices'][0]['message']['content']
    # print(response['choices'][0]['message']['content'])
    
    # ff.write(response['choices'][0]['message']['content']+ "\n---------Part "+str(index+1)+"---------\n")
    # print("Part "+str(index+1))
    list_of_strings[index]=result

def get_language(string):
    print("Language: ")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a specialist in finding out what language a text is written in"},
            {"role": "user", "content": "Which language is the following text written in: "+ string},
            {"role": "assistant", "content": "Reply with only the one word language name of the language the text is written in"},
        ]
    )
    result=response['choices'][0]['message']['content']
    # print(result)
    return result

def translate(string,from_lang,to_lang,window,translated_chunks,index,tries=0):
    print("Translating...")
    try:
        window['-TRANSLATE-'].update(disabled=True)
        window['-TRANSLATED_TEXT-'].update("Translating...")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a the perfect translator for "+from_lang+" to "+to_lang+" your grammar is perfect and you know all the words in both languages the context remains the same and the meaning is the same. You can translate and keep the systax and grammar of the translation perfect."},
                {"role": "user", "content": "Translate the following text from "+from_lang +"to" + to_lang+":"+ string},
                # {"role": "assistant", "content": "You have to translate the text from "+from_lang +"to" + to_lang+" and reply with only the translated text ONLY this is of the utmost importance with perfect grammar and syntax and the meaning should be the same as the original text"},
                {"role": "assistant", "content": "Translate the text from "+from_lang +" to " + to_lang+" and reply with only the translated part. You need to reply with ONLY the translated text!"},
            ]
        )
        result=response['choices'][0]['message']['content']
        # print(result)
        result=verify_translation_and_correct(string,result,from_lang,to_lang)
        translated_chunks[index]=result
        return result
    except Exception as e:
        print(e)
        if tries<=2:
            print("Retrying in 60 seconds")
            time.sleep(60)
            translate(string,from_lang,to_lang,window,translated_chunks,index,tries=tries+1)
        else:
            translated_chunks[index]="\nTranslation failed of :\n"+string +"\n"




def update_when_finished(chunks,window):
    completed_text=""
    for i in range(len(chunks)):
        completed_text+=chunks[i]
    file_name=values['-OUTPUTNAME-']

    window['-TRANSLATION_WORD_COUNT-'].update("Translation Word Count: "+str(len(completed_text.split())))
    window['-TRANSLATED_TEXT-'].update(completed_text)
    f=open(file_name+".txt","w",encoding="utf-8")
    f.write(completed_text)
    f.close()
    window['-TRANSLATE-'].update(disabled=False)

# def split_text_into_chunks(string,chunk_size=512):
#         # Read the entire file content
#         strings = [""]
#         i=0
#         for line in string.splitlines():
            
#             # Count the number of tokens
#             num_tokens = num_tokens_from_string(strings[i],"gpt2")
#             prev_num_tokens=num_tokens_from_string(strings[i-1],"gpt2")
#             print(num_tokens+prev_num_tokens)
#             if num_tokens+prev_num_tokens > chunk_size:
#                 i+=1
#                 strings.append("")
#                 strings[i]+=line
#             else:
#                 strings[i]+=line
#         return strings
def split_text_into_chunks(string, chunk_size=2048):
    # Start with an empty chunk
    chunks = [""]
    i = 0

    # Loop over each line in the string
    for line in string.split("."):
        # Add the current line to the current chunk
        current_chunk = chunks[i] + line

        # Count the number of tokens
        num_tokens = num_tokens_from_string(current_chunk, "gpt-4")

        # If the current chunk exceeds the chunk size limit, start a new chunk
        if num_tokens > chunk_size:
            # Start a new chunk with the current line
            i += 1
            chunks.append(line)
        else:
            # Otherwise, update the current chunk
            chunks[i] = current_chunk

    return chunks

def get_only_lang(string):
        words=string.split(" ")
        lng=""
        for word in words:
            if word in lang_to:
                lng=word
                print("From " + word)
                break
        return lng

def verify_translation_and_correct(original_text,translation_text,from_lang,to_lang):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a the perfect translator for \""+from_lang+"\" to \""+to_lang+"\" your grammar is perfect and you know all the words in both languages the context remains the same and the meaning is the same. You can translate and keep the systax and grammar of the translation perfect."},
                {"role": "user", "content": "I need to verify that the translation from \""+from_lang +"\" to \"" + to_lang+"\" is correct and it has the correct meaning and correct grammar. Original Text: \""+ original_text + "\" Translation: \"" + translation_text+"\"\nOnly and Only reply with the translated text regardless of whether you made any changes to the text or not this is of the atmost importance. The format and newlines need to stay the same as the original text."},
                {"role": "assistant", "content": "You have to verify and correct so that the translation from \""+from_lang +"\" to \"" + to_lang+"\" is correct and reply with the corrected text ONLY (of utmost importance to reply with the tranlated text only) with perfect grammar and syntax and the meaning should be the same as the original text.VERY IMPORTANT : Only reply with the translated text regardless of whether you made any changes to the text or not."},
            ],
            temperature=0.1,
        )
        result=response['choices'][0]['message']['content']
        return result
    except Exception as e:
        print(e)
        return translation_text
        

def thread_handler(chunks,lang,window,values):
        threads=[]
        translated_chunks=[""]*len(chunks)
        num_wait_for_threads=values['-SLIDER-']

        for i in range(len(chunks)):
            # translate(string,from_lang,to_lang,window,translated_chunks,index,tries=0)
            thread=Thread(target=translate,args=(chunks[i],lang,values["-LANGTO-"],window,translated_chunks,i))
            thread.start()
            threads.append(thread)
            if (i+1)%num_wait_for_threads==0:
                print("Waiting for"+str(num_wait_for_threads)+" threads to finish..."+str(i))
                for thread_ in threads:
                    thread_.join()
                threads=[]
        for thread_ in threads:
            thread_.join()
        print("Threads finished")
        Thread(target=update_when_finished,args=(translated_chunks,window)).start()

                

if __name__ == "__main__":

    file_list_column = [
        [
            sg.Text("Text Folder"),
            sg.In(size=(25, 1), enable_events=True, key="-FOLDER-"),
            sg.FolderBrowse(),
        ],
        [
            sg.Listbox(
                values=[], enable_events=True, size=(40, 20), key="-FILE LIST-"
            )
        ],
    ]

    original_lang_text_viewer_column = [
        [sg.Text("Original Language Text:")],
        [sg.Text(size=(40, 1), key="-TOUT-")],
        [sg.Multiline(size=(40,20), key='-ORIGINAL_TEXT-')],
    ]
    translated_lang_text_viewer_column = [
        [sg.Text("Translated Text:")],
        [sg.Text(size=(40, 1), key="-TOUT-")],
        [sg.Multiline(size=(40,20), key='-TRANSLATED_TEXT-')],
    ]
    lang_to = [
    "Afrikaans",
    "Albanian",
    "Amharic",
    "Arabic",
    "Armenian",
    "Azerbaijani",
    "Basque",
    "Belarusian",
    "Bengali",
    "Bosnian",
    "Bulgarian",
    "Catalan",
    "Cebuano",
    "Chichewa",
    "Chinese",
    "Corsican",
    "Croatian",
    "Czech",
    "Danish",
    "Dutch",
    "English",
    "Esperanto",
    "Estonian",
    "Filipino",
    "Finnish",
    "French",
    "Frisian",
    "Galician",
    "Georgian",
    "German",
    "Greek",
    "Gujarati",
    "Haitian Creole",
    "Hausa",
    "Hawaiian",
    "Hebrew",
    "Hindi",
    "Hmong",
    "Hungarian",
    "Icelandic",
    "Igbo",
    "Indonesian",
    "Irish",
    "Italian",
    "Japanese",
    "Javanese",
    "Kannada",
    "Kazakh",
    "Khmer",
    "Korean",
    "Kurdish (Kurmanji)",
    "Kyrgyz",
    "Lao",
    "Latin",
    "Latvian",
    "Lithuanian",
    "Luxembourgish",
    "Macedonian",
    "Malagasy",
    "Malay",
    "Malayalam",
    "Maltese",
    "Maori",
    "Marathi",
    "Mongolian",
    "Myanmar (Burmese)",
    "Nepali",
    "Norwegian",
    "Odia (Oriya)",
    "Pashto",
    "Persian",
    "Polish",
    "Portuguese",
    "Punjabi",
    "Romanian",
    "Russian",
    "Samoan",
    "Scots Gaelic",
    "Serbian",
    "Sesotho",
    "Shona",
    "Sindhi",
    "Sinhala",
    "Slovak",
    "Slovenian",
    "Somali",
    "Spanish",
    "Sundanese",
    "Swahili",
    "Swedish",
    "Tajik",
    "Tamil",
    "Telugu",
    "Thai",
    "Turkish",
    "Ukrainian",
    "Urdu",
    "Uyghur",
    "Uzbek",
    "Vietnamese",
    "Welsh",
    "Xhosa",
    "Yiddish",
    "Yoruba",
    "Zulu"
]
    
    ui_translation_lang_column = [
        [sg.Text("OPEN-API Key:")],
        [sg.Input(key="-API_KEY-",default_text='')],
        [sg.Button("Set Key",key="-SET_KEY-")],
        [sg.Text("Original Words: 0",key='-ORGINAL_WORD_COUNT-')],
        [sg.Text("Translation Word count:",key='-TRANSLATION_WORD_COUNT-')],
        [sg.Text("Select number of threads:")],
        [sg.Slider(range=(1, 30), default_value=5, size=(20, 15), orientation='horizontal', key='-SLIDER-')],
        [sg.Text('From None',key='-ORIGINAL_LANGUAGE-')],
        [sg.Text("Translate to:")], 
        [sg.Combo(lang_to, default_value='English', key='-LANGTO-', size=(20, 1))],
        [sg.Button("Translate",key="-TRANSLATE-")],
        [sg.Text('Output File Name:')],
        [sg.Input(key='-OUTPUTNAME-',default_text='translation')],
         ]
    layout = [
        [
            sg.Column(file_list_column),
            sg.VSeperator(),
            sg.Column(original_lang_text_viewer_column),
            sg.VSeperator(),

            sg.Column(ui_translation_lang_column),
            sg.VSeperator(),
            sg.Column(translated_lang_text_viewer_column),
        ]
    ]
    # Create the window
    window = sg.Window("PerfectTranslator", layout)

    # Create an event loop
    while True:
        event, values = window.read()
        # End program if user closes window or
        # presses the OK button
        if event == "Exit" or event == sg.WIN_CLOSED:
            break
        if event == "-FOLDER-":
            folder = values["-FOLDER-"]
            try:
                # Get list of files in folder
                file_list = os.listdir(folder)
            except:
                file_list = []

            fnames = [
                f
                for f in file_list
                if os.path.isfile(os.path.join(folder, f))
                and f.lower().endswith((".txt"))
            ]
            window["-FILE LIST-"].update(fnames)
        elif event == "-FILE LIST-":  # A file was chosen from the listbox
            try:
                filename = os.path.join(
                values["-FOLDER-"], values["-FILE LIST-"][0]
            )
                window["-TOUT-"].update(filename)
                string=""
                with open(filename,"r",encoding="utf-8") as f:
                    # Read the entire file content
                    string=f.read()
                    window["-ORIGINAL_TEXT-"].update(string)
                chunks=split_text_into_chunks(string,500)
                test_chunks=chunks[random.randint(0,len(chunks)-1)]
                lang=get_language(test_chunks)
                lng=get_only_lang(lang)
                window["-ORIGINAL_LANGUAGE-"].update("From " + lng)
                window["-ORGINAL_WORD_COUNT-"].update("Original Words: "+str(len(string.split())))
            except Exception as e:
                print("Error: ",e)

        elif event == "-TRANSLATE-":
                # window["-TEXT-"].update(filename=filename)
                # print(values["-ORIGINAL_TEXT-"])
                string=values["-ORIGINAL_TEXT-"]
                chunks=split_text_into_chunks(string)
                test_chunks=chunks[random.randint(0,len(chunks)-1)]
                lang=get_language(test_chunks)
                lng=get_only_lang(lang)
                window["-ORIGINAL_LANGUAGE-"].update("From " + lng)
                
                t=Thread(target=thread_handler,args=(chunks,lang,window,values)).start()
        elif event == "-SET_KEY-":
            openai.api_key = values["-API_KEY-"]

                
    window.close()

    exit()
    # Open the file
    strings=["",]
    start=100
    end=122
    i=0
    missing_parts=[41,43,45,48,52,53,57,60,70,84]
    # f = open("GreekText.txt","r",encoding="utf-8")
    # print("The number of tokens in the input string is", num_tokens_from_string(f.read(),"gpt2"))
    # exit()
    with open("GreekText.txt","r",encoding="utf-8") as f:
        # Read the entire file content
        for line in f.readlines():
            strings[i]+=line
            
            # Count the number of tokens
            num_tokens = num_tokens_from_string(strings[i],"gpt2")
            if num_tokens > 2048:
                i+=1
                strings.append("")
            
            # print("The number of tokens in the input string is", num_tokens)

    print(len(strings))
    list_of_strings=[""]*len(strings)
    from threading import Thread
    import time
    threads=[]
    # for i in range(start,end):
    #     t=Thread(target=fix_grammar,args=(strings[i],i))
    #     threads.append(t)
    #     t.start()
    for i in range(0,len(missing_parts)):
        t=Thread(target=fix_grammar,args=(strings[missing_parts[i]-1],missing_parts[i]-1))
        threads.append(t)
        t.start()
        break
    for t in threads:
        t.join()
    ff=open("GreekTextFixed.txt","a",encoding="utf-8")
    # for i in range(start,start+len(list_of_strings)):
    #     string=list_of_strings[i-start]
    #     ff.write("\n---------Part "+str(i+1)+"---------\n")
    #     ff.write(string+ "\n---------Part "+str(i+1)+"---------\n")
    #     print("Part "+str(i+1))
    for i in range(0,len(missing_parts)):
        string=list_of_strings[missing_parts[i]-1]
        ff.write("\n---------Part "+str(missing_parts[i])+"---------\n")
        ff.write(string+ "\n---------Part "+str(missing_parts[i])+"---------\n")
        print("Part "+str(missing_parts[i]))


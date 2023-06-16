# PerfectTranslator
 Translate From One language to Another with the power of AI

 ## PySimpleGUI-OpenAI GPT Translation App
This is a simple GUI application that utilizes the PySimpleGUI library for Python to create an easy-to-use interface for text file translation, powered by OpenAI's GPT.
!["Demo"]("translationDemo2.gig")
### Features
- File browsing: The user can select a directory and it will display all text files in the directory.
- Text Display: Displays the content of the selected text file.
- Language Detection: Identifies the original language of the selected text file.
- Text Translation: Translates the contents of the text file.
- Set OpenAI API key: User can input their OpenAI API key to use for translation.
### Dependencies
    PySimpleGUI
    OpenAI GPT
### How to use
1. Start the application. A GUI window will appear. `python main.py`
2. If you have an OpenAI API key, input it by clicking the "Set Key" button and entering your key in the prompt.
3. To select a file for translation, click on the folder icon. This will open a directory browser. 4. Navigate to the directory containing the text file you wish to translate and select it.
5. The file's contents will be displayed in the window. The original language will also be identified.
6. Click on the "Translate" button to start the translation process. The translated text will be displayed once the process is complete.

Note: This script assumes you have necessary permissions and an active OpenAI account with a valid API key for using OpenAI's GPT.
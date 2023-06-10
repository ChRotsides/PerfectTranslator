api_key="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"

import os
import openai
import tiktoken
from textblob import TextBlob
# openai.organization = "org-NI7ytgnmKiPPOsgBOjK4orYA"
openai.api_key = api_key


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
def fix_grammar(string,index):

        # print(strings[j])
    # ff.write(string+ "\n---------Part "+str(index+1)+"---------\n")
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
    print("Part "+str(index+1))
    list_of_strings[index]=result

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
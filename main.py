!pip install openai==0.28
import openai
import os
model_name = "gpt-3.5-turbo"
#try any method based on your style
os.environ['OPENAI_API_KEY'] = <your-OpenAI-API-key>

#OPENAI_API_KEY = <your-OpenAI-API-key>
#openai.api_key = <your-OpenAI-API-key>
def strict_output(system_prompt, user_prompt, output_format, default_category = "", output_value_only = False,
                  model = 'gpt-3.5-turbo', temperature = 0, num_tries = 2, verbose = False):
    ''' Ensures that OpenAI will always adhere to the desired output json format.
    Uses rule-based iterative feedback to ask GPT to self-correct.
    Keeps trying up to num_tries it it does not. Returns empty json if unable to after num_tries iterations.
    If output field is a list, will treat as a classification problem and output best classification category.
    Text enclosed within < > will generated by GPT accordingly'''

    # if the user input is in a list, we also process the output as a list of json
    list_input = isinstance(user_prompt, list)
    # if the output format contains dynamic elements of < or >, then add to the prompt to handle dynamic elements
    dynamic_elements = '<' in str(output_format)
    # if the output format contains list elements of [ or ], then we add to the prompt to handle lists
    list_output = '[' in str(output_format)

    # start off with no error message
    error_msg = ''

    for i in range(num_tries):

        output_format_prompt = f'''\nYou are to output the following in json format: {output_format}.
Do not put quotation marks or escape character \ in the output fields.'''

        if list_output:
            output_format_prompt += f'''\nIf output field is a list, classify output into the best element of the list.'''

        # if output_format contains dynamic elements, process it accordingly
        if dynamic_elements:
            output_format_prompt += f'''
Any text enclosed by < and > indicates you must generate content to replace it. Example input: Go to <location>, Example output: Go to the garden
Any output key containing < and > indicates you must generate the key name to replace it. Example input: {{'<location>': 'description of location'}}, Example output: {{'school': 'a place for education'}}'''

        # if input is in a list format, ask it to generate json in a list
        if list_input:
            output_format_prompt += '''\nGenerate a list of json, one json for each input element.'''

        # Use OpenAI to get a response
        response = openai.ChatCompletion.create(
          temperature = temperature,
          model=model,
          messages=[
            {"role": "system", "content": system_prompt + output_format_prompt + error_msg},
            {"role": "user", "content": str(user_prompt)}
          ]
        )

        res = response['choices'][0]['message']['content'].replace('\'', '"')

        # ensure that we don't replace away aprostophes in text
        res = re.sub(r"(\w)\"(\w)", r"\1'\2", res)

        if verbose:
            print('System prompt:', system_prompt + output_format_prompt + error_msg)
            print('\nUser prompt:', str(user_prompt))
            print('\nGPT response:', res)

        # try-catch block to ensure output format is adhered to
        try:
            output = json.loads(res)
            if isinstance(user_prompt, list):
                if not isinstance(output, list): raise Exception("Output format not in a list of json")
            else:
                output = [output]

            # check for each element in the output_list, the format is correctly adhered to
            for index in range(len(output)):
                for key in output_format.keys():
                    # unable to ensure accuracy of dynamic output header, so skip it
                    if '<' in key or '>' in key: continue
                    # if output field missing, raise an error
                    if key not in output[index]: raise Exception(f"{key} not in json output")
                    # check that one of the choices given for the list of words is an unknown
                    if isinstance(output_format[key], list):
                        choices = output_format[key]
                        # ensure output is not a list
                        if isinstance(output[index][key], list):
                            output[index][key] = output[index][key][0]
                        # output the default category (if any) if GPT is unable to identify the category
                        if output[index][key] not in choices and default_category:
                            output[index][key] = default_category
                        # if the output is a description format, get only the label
                        if ':' in output[index][key]:
                            output[index][key] = output[index][key].split(':')[0]

                # if we just want the values for the outputs
                if output_value_only:
                    output[index] = [value for value in output[index].values()]
                    # just output without the list if there is only one element
                    if len(output[index]) == 1:
                        output[index] = output[index][0]

            return output if list_input else output[0]

        except Exception as e:
            error_msg = f"\n\nResult: {res}\n\nError message: {str(e)}"
            print("An exception occurred:", str(e))

            print("Current invalid json format:", res)

    return {}
context = '''Apple announced the MacNCheese Pro in 2025. It proved a big hit.
Apple gave Cheese a rousing ovation in 2026 after he invented the MacNCheese Pro in 2024.
Orange created a competing product called the OrangeNCheese Pro.
It's price was slightly higher at $5000, compared to Apple's $4000'''
question = "When did apple announce the MacNCheese Pro?"

import re
import json
res = strict_output(system_prompt = '''You are a knowledge graph builder.
You are to output relations between two objects in the form [object_1, relation, object_2].
All information about dates must be included.
Example Input: John bought a laptop
Example Output: [['John', 'bought', 'laptop']]
Example Input: John built a house in 2019
Example Output: [['John', 'built', 'house'], ['house', 'built in', '2019']]''',
                    user_prompt = context,
                    output_format = {"Knowledge Graph": "List of relations of the form [object_1, relation, object_2]"})
print(res)
kg = res['Knowledge Graph']
res = strict_output(system_prompt = f'''You are a knowledge graph parser.
Only output the relations that are relevant to the question.
Knowledge graph: {kg}''',
                    # user_prompt = f'''Question: {question}''',
                    user_prompt = '''"Question": "{question}"''',
                    output_format = {"Parsed Knowledge Graph": "List of relations of the strictly in the form [object1, relation, object2]"})
print(res)
parsed_kg = res['Parsed Knowledge Graph']

res = strict_output(system_prompt = f'''Use the knowledge graph to answer the following question.
If you are unsure, output 'No Info'
Knowledge Graph: {parsed_kg}''',
                    user_prompt = f'''Question: {question}''',
                    output_format = {"Answer": "Answer question using knowledge graph"})
print('Question:', question)
print('Answer:', res['Answer'])

